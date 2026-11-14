"""Job 1: preços. CheapShark (USD→BRL via PTAX) + Steam (BRL real) → price_snapshots (upsert do dia)."""
import logging
import re

from etl import config, fx, matching
from etl.clients import epic, gog, instant_gaming, nuuvem, steam
from etl.clients.cheapshark import CheapSharkClient, deal_url
from etl.db import connect
from etl.http import HttpClient, RateLimited
from etl.tracked import load_tracked

log = logging.getLogger("etl.jobs.prices")

STEAM_STORE_ID = 1
GOG_STORE_ID = 7        # mesmos ids da CheapShark: o preço real em BRL substitui a estimativa dessas lojas
EPIC_STORE_ID = 25
NUUVEM_STORE_ID = 100  # 100 e 101 ficam fora da faixa de ids da CheapShark
IG_STORE_ID = 101

UPSERT_SNAP = """
INSERT INTO price_snapshots (game_id, store_id, snapshot_date, captured_at, price_brl, price_original,
    currency_original, fx_rate, normal_price_brl, discount_pct, deal_url, price_origin, is_simulated)
VALUES (%(game_id)s, %(store_id)s, %(snapshot_date)s, now(), %(price_brl)s, %(price_original)s,
    %(currency_original)s, %(fx_rate)s, %(normal_price_brl)s, %(discount_pct)s, %(deal_url)s, %(price_origin)s, false)
ON CONFLICT (game_id, store_id, snapshot_date) DO UPDATE SET
    captured_at = now(), price_brl = EXCLUDED.price_brl, price_original = EXCLUDED.price_original,
    currency_original = EXCLUDED.currency_original, fx_rate = EXCLUDED.fx_rate,
    normal_price_brl = EXCLUDED.normal_price_brl, discount_pct = EXCLUDED.discount_pct,
    deal_url = EXCLUDED.deal_url, price_origin = EXCLUDED.price_origin, is_simulated = false
"""


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def pick_hit(title: str, hits: list):
    """Escolhe o resultado da busca: título exato (normalizado); senão o primeiro que contém todas as palavras."""
    if not hits:
        return None
    t = _norm(title)
    for h in hits:
        if _norm(h.external) == t:
            return h
    words = t.split()
    for h in hits:
        if all(w in _norm(h.external) for w in words):
            return h
    return hits[0]


def sync_stores(conn, cs: CheapSharkClient) -> int:
    stores = cs.stores()
    for s in stores:
        conn.execute(
            "INSERT INTO stores (store_id, name, is_active) VALUES (%s, %s, %s) "
            "ON CONFLICT (store_id) DO UPDATE SET name = EXCLUDED.name, is_active = EXCLUDED.is_active",
            (s.storeID, s.storeName, bool(s.isActive)),
        )
    conn.commit()
    return len(stores)


def resolve_games(conn, cs: CheapSharkClient) -> int:
    """Garante linha em games para cada título do YAML e resolve o id da CheapShark por busca."""
    resolved = 0
    for entry in load_tracked():
        title = entry["title"]
        slug = config.slugify(title)
        row = conn.execute(
            "INSERT INTO games (title, slug, tracked) VALUES (%s, %s, true) "
            "ON CONFLICT (slug) DO UPDATE SET tracked = true RETURNING game_id, cheapshark_game_id",
            (title, slug),
        ).fetchone()
        conn.commit()
        if entry.get("nuuvem"):
            conn.execute("UPDATE games SET nuuvem_slug = %s WHERE game_id = %s", (entry["nuuvem"], row["game_id"]))
            conn.commit()
        if entry.get("steam_app_id"):  # override editorial quando a CheapShark não informa o app da Steam
            conn.execute("UPDATE games SET steam_app_id = %s WHERE game_id = %s", (entry["steam_app_id"], row["game_id"]))
            conn.commit()
        if row["cheapshark_game_id"]:
            resolved += 1
            continue
        hit = pick_hit(title, cs.search(entry.get("search", title)))
        if not hit:
            log.warning("sem resultado na CheapShark para %r", title)
            continue
        steam_id = int(hit.steamAppID) if hit.steamAppID and hit.steamAppID.isdigit() else None
        conn.execute(
            "UPDATE games SET cheapshark_game_id = %s, steam_app_id = %s WHERE game_id = %s",
            (hit.gameID, entry.get("steam_app_id") or steam_id, row["game_id"]),
        )
        conn.commit()
        resolved += 1
        log.info("resolvido %r → CheapShark %s (steam %s)", title, hit.gameID, steam_id)
    return resolved


STALE_DAYS = 7  # intervalo para tentar de novo descobrir uma loja que ainda não listava o jogo
DISCOVERED_REFRESH_HOURS = 12  # jogos descobertos pela busca são recoletados no máximo a cada 12 h (os do YAML, a cada ciclo)
IG_MAX_CANDIDATES = 3  # páginas da Instant Gaming testadas por jogo (a primeira pode ser de outra região ou estar sem estoque)


def _stale(ts, today) -> bool:
    return ts is None or (today - ts.date()).days >= STALE_DAYS


def _put(conn, g, store_id, today, price, origin, url, normal=None, discount=0, currency="BRL", fx_rate=None, original=None):
    conn.execute(UPSERT_SNAP, {
        "game_id": g["game_id"], "store_id": store_id, "snapshot_date": today, "price_brl": price,
        "price_original": original if original is not None else price, "currency_original": currency,
        "fx_rate": fx_rate, "normal_price_brl": normal if normal is not None else price, "discount_pct": discount,
        "deal_url": url, "price_origin": origin,
    })


def _count(stats, key):
    stats["snapshots"] += 1
    stats[key] = stats.get(key, 0) + 1


def _collect_steam(conn, http, g, detail, today, stats, active) -> None:
    app_id = g["steam_app_id"] or (detail.steam_app_id if detail else None)
    if not (app_id and STEAM_STORE_ID in active):
        return
    try:
        sp = steam.fetch_price_brl(http, app_id)
    except RateLimited:
        raise
    except Exception as exc:
        log.error("steam falhou para %s: %s", g["title"], exc)
        return
    if sp:
        _put(conn, g, STEAM_STORE_ID, today, sp.final_brl, "steam_brl", f"https://store.steampowered.com/app/{app_id}",
             normal=sp.initial_brl, discount=sp.discount_percent)
        _count(stats, "steam_brl")


def _collect_epic(conn, http, g, today, stats, active) -> bool:
    """Preço real da Epic em BRL (sobrescreve a estimativa da CheapShark no dia). Devolve True se gravou."""
    if EPIC_STORE_ID not in active or (not g.get("epic_slug") and not _stale(g.get("epic_checked_at"), today)):
        return False  # a loja não tinha o jogo na última checagem: só tenta de novo depois de STALE_DAYS
    try:
        offer = epic.find_offer(http, g["title"])
        conn.execute("UPDATE games SET epic_slug = %s, epic_checked_at = now() WHERE game_id = %s", (offer.slug if offer else None, g["game_id"]))
    except RateLimited:
        raise
    except Exception as exc:
        log.error("epic falhou para %s: %s", g["title"], exc)
        return False
    if not offer:
        return False
    _put(conn, g, EPIC_STORE_ID, today, offer.price_brl, "epic_brl", offer.url, normal=offer.normal_brl, discount=offer.discount_pct)
    _count(stats, "epic_brl")
    return True


def _collect_gog(conn, http, g, today, stats, active) -> bool:
    if GOG_STORE_ID not in active:
        return False
    gog_id, slug = g.get("gog_id"), g.get("gog_slug")
    try:
        if not gog_id:
            if not _stale(g.get("gog_checked_at"), today):
                return False
            found = gog.find_product(http, g["title"])
            gog_id, slug = (found.gog_id, found.slug) if found else (None, None)
            conn.execute("UPDATE games SET gog_id = %s, gog_slug = %s, gog_checked_at = now() WHERE game_id = %s", (gog_id, slug, g["game_id"]))
        prices = gog.fetch_price(http, gog_id) if gog_id else None
    except RateLimited:
        raise
    except Exception as exc:
        log.error("gog falhou para %s: %s", g["title"], exc)
        return False
    if not prices:
        return False
    final, normal = prices
    discount = round(float((1 - final / normal) * 100), 2) if normal > 0 else 0
    _put(conn, g, GOG_STORE_ID, today, final, "gog_brl", gog.game_url(slug), normal=normal, discount=discount)
    _count(stats, "gog_brl")
    return True


def _nuuvem_candidates(conn, title: str) -> list[str]:
    """Slugs possíveis do jogo: primeiro os do índice (sitemap oficial), depois os palpites do título."""
    key = matching.norm(title)
    rows = conn.execute("SELECT slug, norm_title FROM nuuvem_catalog WHERE norm_title = %s OR norm_title LIKE %s", (key, key + " %")).fetchall()
    out = nuuvem.pick_slugs(rows, title)
    return out + [s for s in nuuvem.slug_guesses(title) if s not in out]


def _collect_nuuvem(conn, http, g, today, stats, active) -> None:
    """Usa o slug já conhecido; se ele não rende preço, procura de novo no índice do sitemap (a cada STALE_DAYS)."""
    if NUUVEM_STORE_ID not in active:
        return
    slug, price = g.get("nuuvem_slug"), None
    try:
        if slug:
            price = nuuvem.fetch_price_brl(http, slug)
        if price is None and _stale(g.get("nuuvem_checked_at"), today):
            slug = None
            for cand in _nuuvem_candidates(conn, g["title"]):
                price = nuuvem.fetch_price_brl(http, cand)
                if price is not None:
                    slug = cand
                    break
            conn.execute("UPDATE games SET nuuvem_slug = %s, nuuvem_checked_at = now() WHERE game_id = %s", (slug, g["game_id"]))
    except RateLimited:
        raise
    except Exception as exc:
        log.error("nuuvem falhou para %s: %s", g["title"], exc)
        return
    if price:
        _put(conn, g, NUUVEM_STORE_ID, today, price, "nuuvem_brl", nuuvem.item_url(slug))
        _count(stats, "nuuvem_brl")


def _collect_instant_gaming(conn, http, g, today, stats, active) -> None:
    """Usa a página já conhecida; se ela não rende preço em BRL (outra região, sem estoque), testa as demais do índice."""
    if IG_STORE_ID not in active:
        return
    url, price = g.get("instant_gaming_url"), None
    try:
        if url:
            price = instant_gaming.fetch_price_brl(http, url)
        if price is None and _stale(g.get("ig_checked_at"), today):
            key = matching.norm(g["title"])
            rows = conn.execute("SELECT ig_id, url, platform, norm_title FROM ig_catalog WHERE norm_title = %s OR norm_title LIKE %s",
                                (key, key + " %")).fetchall()
            rows = [r for r in rows if matching.title_matches(g["title"], r["norm_title"])]  # a mesma obra (ou edição), nunca sequência/DLC
            url = None
            for cand in instant_gaming.rank(rows)[:IG_MAX_CANDIDATES]:
                price = instant_gaming.fetch_price_brl(http, cand["url"])
                if price is not None:
                    url = cand["url"]
                    break
            conn.execute("UPDATE games SET instant_gaming_url = %s, ig_checked_at = now() WHERE game_id = %s", (url, g["game_id"]))
    except RateLimited:
        raise
    except Exception as exc:
        log.error("instant gaming falhou para %s: %s", g["title"], exc)
        return
    if price:
        _put(conn, g, IG_STORE_ID, today, price, "instantgaming_brl", url)
        _count(stats, "instantgaming_brl")


def _resolve_ids(conn, http, cs, g, today) -> None:
    """Jogo achado só numa loja (ex.: GOG ou Epic) ainda não tem id na CheapShark nem na Steam: procura pelo título (a cada STALE_DAYS)."""
    if not g["cheapshark_game_id"] and _stale(g.get("cs_checked_at"), today):
        hit = cs.by_steam_app_id(g["steam_app_id"]) if g["steam_app_id"] else None  # o app da Steam é exato; o título é só plano B
        hit = hit or matching.best_match(g["title"], cs.search(g["title"]), key=lambda h: h.external)
        if hit:
            sid = int(hit.steamAppID) if hit.steamAppID and hit.steamAppID.isdigit() else None
            g["cheapshark_game_id"], g["steam_app_id"] = hit.gameID, g["steam_app_id"] or sid
            conn.execute("UPDATE games SET cheapshark_game_id = %s, steam_app_id = COALESCE(steam_app_id, %s) WHERE game_id = %s",
                         (hit.gameID, sid, g["game_id"]))
        conn.execute("UPDATE games SET cs_checked_at = now() WHERE game_id = %s", (g["game_id"],))
    if not g["steam_app_id"] and _stale(g.get("steam_checked_at"), today):
        hit = matching.best_match(g["title"], steam.search(http, g["title"]), key=lambda h: h["name"])
        if hit:
            g["steam_app_id"] = hit["id"]
            conn.execute("UPDATE games SET steam_app_id = %s WHERE game_id = %s", (hit["id"], g["game_id"]))
        conn.execute("UPDATE games SET steam_checked_at = now() WHERE game_id = %s", (g["game_id"],))


def refresh_game(conn, http, cs, g, rate, active, today, stats, with_deals: bool = True) -> None:
    """Coleta o preço de UM jogo em todas as fontes: CheapShark (USD→BRL) e, em BRL real, Steam, Epic, GOG, Nuuvem e Instant Gaming.
    `with_deals=False` pula a chamada de ofertas da CheapShark (usado na recoleta em massa das lojas, que não precisa dela)."""
    try:
        _resolve_ids(conn, http, cs, g, today)
    except RateLimited:
        raise
    except Exception as exc:  # sem os ids o jogo ainda é coletado nas demais lojas
        log.error("resolução de ids falhou para %s: %s", g["title"], exc)
        conn.rollback()
    detail = cs.game(g["cheapshark_game_id"]) if with_deals and g["cheapshark_game_id"] else None
    # Lojas com preço real já gravado hoje não são sobrescritas pela estimativa da CheapShark.
    real = {r["store_id"] for r in conn.execute(
        "SELECT store_id FROM price_snapshots WHERE game_id = %s AND snapshot_date = %s AND price_origin <> 'converted_usd'",
        (g["game_id"], today))}
    if _collect_epic(conn, http, g, today, stats, active):
        real.add(EPIC_STORE_ID)
    if _collect_gog(conn, http, g, today, stats, active):
        real.add(GOG_STORE_ID)
    for d in (detail.deals if detail else []):
        if d.storeID == STEAM_STORE_ID or d.storeID in real or d.storeID not in active:
            continue  # Steam e as lojas com preço real vêm em BRL; lojas inativas ignoradas
        _put(conn, g, d.storeID, today, fx.to_brl(d.price, rate), "converted_usd", deal_url(d.dealID),
             normal=fx.to_brl(d.retailPrice, rate), discount=round(d.savings, 2), currency="USD", fx_rate=rate, original=d.price)
        _count(stats, "converted_usd")
    _collect_steam(conn, http, g, detail, today, stats, active)
    _collect_nuuvem(conn, http, g, today, stats, active)
    _collect_instant_gaming(conn, http, g, today, stats, active)
    conn.commit()


GAME_COLS = ("game_id, title, cheapshark_game_id, steam_app_id, nuuvem_slug, nuuvem_checked_at, instant_gaming_url, ig_checked_at, "
             "epic_slug, epic_checked_at, gog_id, gog_slug, gog_checked_at, steam_checked_at, cs_checked_at")


def run(conn=None, http=None, today=None) -> dict:
    own = conn is None
    conn = conn or connect()
    http = http or HttpClient()
    today = today or config.today_br()
    cs = CheapSharkClient(http)
    stats = {"games": 0, "snapshots": 0, "steam_brl": 0, "converted_usd": 0, "failed": 0}
    try:
        sync_stores(conn, cs)
        try:
            resolve_games(conn, cs)
        except RateLimited as exc:
            log.error("%s durante a resolução de jogos; seguindo com os já resolvidos", exc)
        found = fx.rate_from_db(conn, today)
        if not found:
            from etl.jobs import fx as fx_job

            fx_job.run(conn=conn, http=http)
            found = fx.rate_from_db(conn, today)
        if not found:
            raise RuntimeError("sem cotação PTAX disponível; abortando job de preços")
        rate_date, rate = found
        log.info("cotação usada: %s (venda %s)", rate_date, rate)
        active = {r["store_id"] for r in conn.execute("SELECT store_id FROM stores WHERE is_active")}
        games = conn.execute(
            f"SELECT {GAME_COLS} FROM games "
            "WHERE tracked AND (NOT discovered OR NOT EXISTS (SELECT 1 FROM price_snapshots p WHERE p.game_id = games.game_id "
            f"AND NOT p.is_simulated AND p.captured_at > now() - interval '{DISCOVERED_REFRESH_HOURS} hours')) ORDER BY game_id"
        ).fetchall()
        for g in games:
            stats["games"] += 1
            try:
                refresh_game(conn, http, cs, g, rate, active, today, stats)
            except RateLimited as exc:
                log.error("%s; interrompendo o ciclo (retomado no próximo)", exc)
                stats["failed"] += 1
                stats["rate_limited"] = True
                break
            except Exception as exc:
                log.error("falha em %s: %s", g["title"], exc)
                stats["failed"] += 1
                conn.rollback()
        log.info("prices: %s", stats)
        return stats
    finally:
        if own:
            conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())

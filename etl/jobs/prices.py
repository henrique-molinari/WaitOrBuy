"""Job 1: preços. CheapShark (USD→BRL via PTAX) + Steam (BRL real) → price_snapshots (upsert do dia)."""
import logging
import re

from etl import config, fx
from etl.clients import steam
from etl.clients.cheapshark import CheapSharkClient, deal_url
from etl.db import connect
from etl.http import HttpClient, RateLimited
from etl.tracked import load_tracked

log = logging.getLogger("etl.jobs.prices")

STEAM_STORE_ID = 1

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
            "SELECT game_id, title, cheapshark_game_id, steam_app_id FROM games "
            "WHERE tracked AND cheapshark_game_id IS NOT NULL ORDER BY game_id"
        ).fetchall()
        for g in games:
            stats["games"] += 1
            try:
                detail = cs.game(g["cheapshark_game_id"])
            except RateLimited as exc:
                log.error("%s; interrompendo o ciclo (retomado no próximo)", exc)
                stats["failed"] += 1
                stats["rate_limited"] = True
                break
            except Exception as exc:
                log.error("falha em %s: %s", g["title"], exc)
                stats["failed"] += 1
                continue
            for d in detail.deals:
                if d.storeID == STEAM_STORE_ID or d.storeID not in active:
                    continue  # Steam vem em BRL real; lojas inativas ignoradas
                price_brl = fx.to_brl(d.price, rate)
                normal = fx.to_brl(d.retailPrice, rate)
                conn.execute(UPSERT_SNAP, {
                    "game_id": g["game_id"], "store_id": d.storeID, "snapshot_date": today,
                    "price_brl": price_brl, "price_original": d.price, "currency_original": "USD",
                    "fx_rate": rate, "normal_price_brl": normal, "discount_pct": round(d.savings, 2),
                    "deal_url": deal_url(d.dealID), "price_origin": "converted_usd",
                })
                stats["snapshots"] += 1
                stats["converted_usd"] += 1
            app_id = g["steam_app_id"] or detail.steam_app_id
            if app_id and STEAM_STORE_ID in active:
                try:
                    sp = steam.fetch_price_brl(http, app_id)
                except Exception as exc:
                    log.error("steam falhou para %s: %s", g["title"], exc)
                    sp = None
                if sp:
                    conn.execute(UPSERT_SNAP, {
                        "game_id": g["game_id"], "store_id": STEAM_STORE_ID, "snapshot_date": today,
                        "price_brl": sp.final_brl, "price_original": sp.final_brl, "currency_original": "BRL",
                        "fx_rate": None, "normal_price_brl": sp.initial_brl, "discount_pct": sp.discount_percent,
                        "deal_url": f"https://store.steampowered.com/app/{app_id}", "price_origin": "steam_brl",
                    })
                    stats["snapshots"] += 1
                    stats["steam_brl"] += 1
            conn.commit()
        log.info("prices: %s", stats)
        return stats
    finally:
        if own:
            conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())

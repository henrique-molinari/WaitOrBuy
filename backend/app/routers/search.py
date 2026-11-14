"""Busca em todas as plataformas conectadas: filtros, ordenação, autocompletar e descoberta ao vivo."""
import logging
import os
import re
import time

from fastapi import APIRouter, Depends, Query

from app import db
from app.errors import AppError
from app.routers.public import mongo_meta
from app.schemas import PlatformsResponse, RecommendedResponse, SearchResponse, SuggestResponse
from app.services import pricing

router = APIRouter(tags=["busca"])
NORM_TITLE = "regexp_replace(unaccent(title), '[''’`´]', '', 'g')"  # título sem acento nem apóstrofo, para comparar com o termo
log = logging.getLogger("app.search")

LIVE_TTL = 6 * 3600
_LIVE_SEEN: dict[str, float] = {}   # consulta normalizada → quando a descoberta ao vivo rodou
BRL_STORES = {
    1: "Steam (API oficial)", 7: "GOG (catálogo público)", 25: "Epic Games Store (GraphQL público da loja)",
    100: "Nuuvem (página do produto)", 101: "Instant Gaming (sitemap + página do produto)",
}
SORTS = ("relevance", "price", "discount", "title", "stores")


def _plain(term: str) -> str:
    """Sem apóstrofos ("Baldur's" = "Baldurs"), igual ao que o SQL faz com o título (NORM_TITLE)."""
    return re.sub(r"['’`´]", "", term)


def wob_letters(term: str) -> str:
    """Só letras e números do termo (para não rodar busca parecida com '??' ou '--')."""
    return re.sub(r"[\W_]+", "", term)


def _like(term: str) -> str:
    return "%" + _plain(term).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


FUZZY_MIN = 0.35   # similaridade mínima (0–1) para considerar "parecido"; abaixo disso é ruído


def fuzzy_games(conn, q: str, limit: int = 300) -> list[dict]:
    """Jogos com título parecido com `q` (erro de digitação, letra trocada, palavra faltando), do mais ao menos parecido.

    Nota = maior entre similaridade de trigramas (pg_trgm) e, para termo de uma palavra com 5+ letras, 1 − distância de edição
    (levenshtein) até a palavra mais próxima do título, aceitando no máximo 1 erro a cada 3 letras."""
    return conn.execute(
        "WITH q AS (SELECT wob_norm(%s) AS qn) "
        "SELECT game_id, slug, title, discovered, score FROM ("
        " SELECT g.game_id, g.slug, g.title, g.discovered, greatest(similarity(wob_norm(g.title), q.qn), word_similarity(q.qn, wob_norm(g.title)),"
        "  coalesce((SELECT 1.0 - min(levenshtein(w, q.qn))::float / length(q.qn) FROM regexp_split_to_table(wob_norm(g.title), ' ') w"
        "            WHERE strpos(q.qn, ' ') = 0 AND length(q.qn) >= 5 AND levenshtein(w, q.qn) <= length(q.qn) / 3), 0)) AS score"
        " FROM games g, q WHERE g.tracked) t WHERE score >= %s ORDER BY score DESC, length(title), title LIMIT %s", (q, FUZZY_MIN, limit)).fetchall()


def live_discover(conn, q: str) -> tuple[int, str | None]:
    """Procura o jogo nas lojas conectadas quando o banco ainda não o conhece (no máximo 1x a cada 6 h por consulta)."""
    key = " ".join(q.lower().split())
    now = time.time()
    if len(key) < 3 or now - _LIVE_SEEN.get(key, 0) < LIVE_TTL:
        return 0, None
    _LIVE_SEEN[key] = now
    try:
        from etl.discovery import discover
        from etl.http import HttpClient

        return len(discover(conn, HttpClient(pause=0.3, retries=1), q)), None
    except Exception as exc:  # fontes externas fora do ar não derrubam a busca
        log.warning("descoberta ao vivo falhou para %r: %s", q, exc)
        _LIVE_SEEN.pop(key, None)
        conn.rollback()
        return 0, "Algumas lojas não responderam agora; mostrando o que já temos."


def _sorter(sort: str):
    return {
        "price": lambda r: r["best_offer"]["price_brl"],
        "discount": lambda r: -max(o["discount_pct"] for o in r["offers"]),
        "title": lambda r: r["title"].lower(),
        "stores": lambda r: -len(r["offers"]),
    }.get(sort)


@router.get("/api/search", response_model=SearchResponse)
def search(q: str = Query("", max_length=100), limit: int = Query(24, ge=1, le=60),
           store: list[int] = Query(default=[]), max_price: float | None = Query(None, gt=0),
           min_discount: float = Query(0, ge=0, le=100), sort: str = Query("relevance"),
           live: bool = Query(True), conn=Depends(db.get_conn)):
    """Filtros: loja(s), preço máximo, desconto mínimo; ordenação; `live` procura jogos novos nas lojas. Sem `q`, navega o catálogo."""
    q = q.strip()
    if sort not in SORTS:
        raise AppError(422, "invalid_sort", f"Ordenação inválida. Use: {', '.join(SORTS)}.")
    discovered, live_error = live_discover(conn, q) if live and q else (0, None)
    where, args = ["tracked"], []
    for word in q.split()[:6]:
        where.append(f"{NORM_TITLE} ILIKE unaccent(%s)")
        args.append(_like(word))
    games = conn.execute(
        f"SELECT game_id, slug, title, discovered FROM games WHERE {' AND '.join(where)} "
        f"ORDER BY (lower({NORM_TITLE}) = lower(unaccent(%s))) DESC, (lower({NORM_TITLE}) LIKE lower(unaccent(%s))) DESC, length(title), title LIMIT 300",
        (*args, _plain(q), _plain(q).replace("%", "").replace("_", "") + "%")).fetchall()
    fuzzy = False
    if q and not games and len(wob_letters(q)) >= 3:  # nada contém o termo: tenta títulos parecidos (erro de digitação)
        games = fuzzy_games(conn, q)
        fuzzy = bool(games)
    did_you_mean = games[0]["title"] if fuzzy else None
    ids = [g["game_id"] for g in games]
    offers = pricing.offers_by_game(conn, ids) if ids else {}
    meta = mongo_meta(ids)
    rows, facet = [], {}
    for g in games:
        offs = offers.get(g["game_id"], [])
        for o in offs:
            f = facet.setdefault(o["store_id"], {"store_id": o["store_id"], "name": o["store_name"], "count": 0})
            f["count"] += 1
        if store:
            offs = [o for o in offs if o["store_id"] in store]
        if max_price is not None:
            offs = [o for o in offs if o["price_brl"] <= max_price]
        if min_discount:
            offs = [o for o in offs if o["discount_pct"] >= min_discount]
        if not offs:
            continue
        m = meta.get(g["game_id"], {})
        rows.append({"game_id": g["game_id"], "slug": g["slug"], "title": g["title"], "thumb": m.get("background_image"),
                     "best_offer": offs[0], "offers": offs, "is_fixture": m.get("is_fixture"),
                     "genres": m.get("genres") or [], "discovered": g["discovered"]})
    key = _sorter(sort)
    if key:
        rows.sort(key=key)
    rows = rows[:limit]
    return {"query": q, "count": len(rows), "results": rows, "discovered": discovered, "live_error": live_error,
            "fuzzy": fuzzy, "did_you_mean": did_you_mean,
            "facets": sorted(facet.values(), key=lambda f: (-f["count"], f["name"]))}


LIVE_SUGGEST_TTL = 3600
_LIVE_SUGGEST: dict[str, tuple[float, list[str]]] = {}


def live_suggestions(term: str, known_titles: list[str], max_items: int) -> list[dict]:
    """Jogos da Steam (preço em BRL, só jogo-base) que combinam com o texto e ainda não estão no banco. Falha em silêncio."""
    key = " ".join(term.lower().split())
    now = time.time()
    hit = _LIVE_SUGGEST.get(key)
    if hit and now - hit[0] < LIVE_SUGGEST_TTL:
        names = hit[1]
    else:
        try:
            from etl.clients import steam
            from etl.discovery import clean_title
            from etl.http import HttpClient

            names = [clean_title(r["name"]) for r in steam.search(HttpClient(pause=0, retries=0, timeout=3.0), term)]
        except Exception as exc:  # sem Steam, o autocompletar segue só com o banco
            log.warning("sugestão ao vivo falhou para %r: %s", term, exc)
            return []
        if len(_LIVE_SUGGEST) > 500:
            _LIVE_SUGGEST.clear()
        _LIVE_SUGGEST[key] = (now, names)
    from etl.matching import norm

    have = {norm(t) for t in known_titles}
    roman = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}

    def looks_like_dlc(n: str) -> bool:
        """Estende um jogo que já temos com palavras que não são número de sequência ("Forza Horizon 6 VIP", "Elden Ring Shadow of…")."""
        for b in have:
            if norm(n).startswith(b + " "):
                first = norm(n)[len(b) + 1:].split()[0]
                return not (first.isdigit() or first in roman)
        return False

    out, seen = [], set()
    for n in names:
        if norm(n) in have or norm(n) in seen or looks_like_dlc(n):
            continue
        seen.add(norm(n))
        out.append({"game_id": None, "slug": None, "title": n, "live": True})
    return out[:max_items]


@router.get("/api/suggest", response_model=SuggestResponse)
def suggest(q: str = Query(min_length=1, max_length=100), live: bool = Query(True), conn=Depends(db.get_conn)):
    """Autocompletar: banco local primeiro; se houver menos de 5 acertos, completa com jogos da Steam ao vivo (cache de 1 h por texto)."""
    term = q.strip()
    rows = conn.execute(
        f"SELECT game_id, slug, title FROM games WHERE tracked AND {NORM_TITLE} ILIKE unaccent(%s) "
        f"ORDER BY ({NORM_TITLE} ILIKE unaccent(%s)) DESC, length(title), title LIMIT 8", (_like(term), _like(term)[1:])).fetchall()
    if not rows and len(wob_letters(term)) >= 3:  # sem acerto exato: sugere títulos parecidos
        rows = fuzzy_games(conn, term, 8)
    out = [{"game_id": r["game_id"], "slug": r["slug"], "title": r["title"], "live": False} for r in rows]
    if len(out) < 5 and live and len(wob_letters(term)) >= 3:  # banco local pequeno: completa com a Steam ao vivo
        out += live_suggestions(term, [r["title"] for r in rows], 8 - len(out))
    return {"query": q, "suggestions": out}


@router.get("/api/recommended", response_model=RecommendedResponse)
def recommended(exclude: list[int] = Query(default=[], max_length=60), limit: int = Query(8, ge=1, le=24), conn=Depends(db.get_conn)):
    """Jogos para sugerir abaixo da lista de busca: mesmo gênero dos jogos em `exclude` primeiro, depois os de maior desconto."""
    rows = conn.execute(
        "SELECT DISTINCT ON (l.game_id) l.*, g.slug, g.title FROM v_latest_price l JOIN games g USING (game_id) "
        "WHERE g.tracked AND NOT (g.game_id = ANY(%s)) ORDER BY l.game_id, l.price_brl", (exclude,)).fetchall()
    want = {g for m in mongo_meta(exclude).values() for g in (m.get("genres") or [])}
    meta = mongo_meta([r["game_id"] for r in rows])
    scored = []
    for r in rows:
        m = meta.get(r["game_id"], {})
        shared = len(want & set(m.get("genres") or []))
        scored.append((shared * 100 + float(r["discount_pct"] or 0), shared, r, m))
    scored.sort(key=lambda t: (-t[0], t[2]["title"]))
    items = [{"game_id": r["game_id"], "slug": r["slug"], "title": r["title"], "thumb": m.get("background_image"),
              "offer": pricing.offer_from_row(r), "reason": "genero" if shared else "promocao"} for _, shared, r, m in scored[:limit]]
    return {"count": len(items), "items": items}


def _kind(real: int, estimated: int) -> str:
    """Honestidade dos dados: 'brl_real' só se TODA oferta vigente da loja é preço real; 'mixed' se parte ainda é estimativa."""
    if not estimated:
        return "brl_real"
    return "mixed" if real else "usd_converted"


def _source(store_id: int, real: int) -> str:
    return BRL_STORES[store_id] if store_id in BRL_STORES and real else "CheapShark (USD convertido pelo PTAX)"


@router.get("/api/platforms", response_model=PlatformsResponse)
def platforms(conn=Depends(db.get_conn)):
    """Plataformas conectadas (lojas com ofertas reais coletadas) e provedores de dados."""
    rows = conn.execute(
        "SELECT s.store_id, s.name, s.domain, count(DISTINCT l.game_id) AS games, max(l.captured_at) AS last, "
        "count(*) FILTER (WHERE l.price_origin = 'converted_usd') AS estimated, count(*) FILTER (WHERE l.price_origin <> 'converted_usd') AS real "
        "FROM stores s JOIN v_latest_price l USING (store_id) WHERE s.is_active "
        "GROUP BY s.store_id, s.name, s.domain ORDER BY games DESC, s.name").fetchall()
    out = [{"store_id": r["store_id"], "name": r["name"], "domain": r["domain"],
            "price_kind": _kind(r["real"], r["estimated"]),
            "source": _source(r["store_id"], r["real"]),
            "games": r["games"], "last_captured_at": r["last"].isoformat() if r["last"] else None} for r in rows]
    total = conn.execute("SELECT count(*) AS n FROM games WHERE tracked").fetchone()["n"]
    providers = [
        {"name": "CheapShark", "role": "Preços e busca em 13 lojas (USD)", "needs_key": False, "enabled": True},
        {"name": "Steam Store API", "role": "Preço real em BRL e metadados", "needs_key": False, "enabled": True},
        {"name": "GOG", "role": "Preço real em BRL (catálogo e preços públicos)", "needs_key": False, "enabled": True},
        {"name": "Epic Games Store", "role": "Preço real em BRL (GraphQL público da loja)", "needs_key": False, "enabled": True},
        {"name": "Nuuvem", "role": "Preço real em BRL (página do produto)", "needs_key": False, "enabled": True},
        {"name": "Instant Gaming", "role": "Preço real em BRL (sitemap + página do produto)", "needs_key": False, "enabled": True},
        {"name": "Banco Central (PTAX)", "role": "Câmbio USD→BRL", "needs_key": False, "enabled": True},
        {"name": "RAWG", "role": "Gêneros, nota e tempo de jogo", "needs_key": True, "enabled": bool(os.getenv("RAWG_API_KEY", "").strip())},
    ]
    return {"count": len(out), "platforms": out, "providers": providers, "total_games": total}

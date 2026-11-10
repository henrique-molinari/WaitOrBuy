"""Busca em todas as plataformas conectadas: filtros, ordenação, autocompletar e descoberta ao vivo."""
import logging
import os
import re
import time

from fastapi import APIRouter, Depends, Query

from app import db
from app.errors import AppError
from app.routers.public import mongo_meta
from app.schemas import PlatformsResponse, SearchResponse, SuggestResponse
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


def _like(term: str) -> str:
    return "%" + _plain(term).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


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
            "facets": sorted(facet.values(), key=lambda f: (-f["count"], f["name"]))}


@router.get("/api/suggest", response_model=SuggestResponse)
def suggest(q: str = Query(min_length=1, max_length=100), conn=Depends(db.get_conn)):
    """Autocompletar rápido (só banco local, sem chamar lojas)."""
    term = q.strip()
    rows = conn.execute(
        f"SELECT game_id, slug, title FROM games WHERE tracked AND {NORM_TITLE} ILIKE unaccent(%s) "
        f"ORDER BY ({NORM_TITLE} ILIKE unaccent(%s)) DESC, length(title), title LIMIT 8", (_like(term), _like(term)[1:])).fetchall()
    return {"query": q, "suggestions": rows}


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

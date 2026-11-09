from app import db
from app.errors import AppError
from app.schemas import DealsResponse, FxOut, GameDetail, History, SearchResponse
from app.services import pricing
from fastapi import APIRouter, Depends, Query

router = APIRouter()


def mongo_meta(ids: list[int]) -> dict[int, dict]:
    if not ids:
        return {}
    try:
        return {d["game_id"]: d for d in db.mongo_games().find({"game_id": {"$in": ids}}, {"_id": 0})}
    except Exception:
        return {}


@router.get("/api/search", response_model=SearchResponse, tags=["busca"])
def search(q: str = Query(min_length=1, max_length=100), limit: int = Query(20, ge=1, le=50),
           conn=Depends(db.get_conn)):
    like = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    games = conn.execute(
        "SELECT game_id, slug, title FROM games WHERE tracked AND title ILIKE %s "
        "ORDER BY (lower(title) = lower(%s)) DESC, title LIMIT %s", (like, q.strip(), limit)).fetchall()
    ids = [g["game_id"] for g in games]
    offers = pricing.offers_by_game(conn, ids) if ids else {}
    meta = mongo_meta(ids)
    results = []
    for g in games:
        offs = offers.get(g["game_id"], [])
        m = meta.get(g["game_id"], {})
        results.append({"game_id": g["game_id"], "slug": g["slug"], "title": g["title"],
                        "thumb": m.get("background_image"), "best_offer": offs[0] if offs else None,
                        "offers": offs, "is_fixture": m.get("is_fixture")})
    return {"query": q, "count": len(results), "results": results}


@router.get("/api/games/{game_id}", response_model=GameDetail, tags=["jogos"])
def game_detail(game_id: int, conn=Depends(db.get_conn)):
    g = conn.execute("SELECT game_id, slug, title FROM games WHERE game_id = %s", (game_id,)).fetchone()
    if not g:
        raise AppError(404, "not_found", "Jogo não encontrado.")
    offers = pricing.offers_by_game(conn, [game_id])[game_id]
    best = offers[0] if offers else None
    stats = pricing.game_stats(conn, game_id)
    sale = pricing.next_sale_info(conn)
    meta = mongo_meta([game_id]).get(game_id, {})
    playtime = meta.get("playtime_hours")
    return {
        "game_id": g["game_id"], "slug": g["slug"], "title": g["title"],
        "meta": {k: meta.get(k) for k in ("background_image", "rating", "metacritic", "released", "description",
                                          "playtime_hours", "is_fixture")}
        | {"genres": meta.get("genres") or [], "platforms": meta.get("platforms") or []},
        "offers": offers, "best_offer": best, "stats": stats,
        "verdict": pricing.build_verdict(best, stats, sale),
        "next_sale": sale, "playtime_hours": playtime,
        "price_per_hour": pricing.price_per_hour(best["price_brl"] if best else None, playtime),
    }


@router.get("/api/games/{game_id}/history", response_model=History, tags=["jogos"])
def history(game_id: int, store: int | None = Query(None, gt=0), days: int = Query(180, ge=1, le=730),
            conn=Depends(db.get_conn)):
    if not conn.execute("SELECT 1 FROM games WHERE game_id = %s", (game_id,)).fetchone():
        raise AppError(404, "not_found", "Jogo não encontrado.")
    since = db.today().toordinal() - days
    from datetime import date

    since_d = date.fromordinal(since)
    if store is None:
        rows = conn.execute(
            "SELECT DISTINCT ON (snapshot_date) snapshot_date, price_brl, store_id, is_simulated FROM price_snapshots "
            "WHERE game_id = %s AND snapshot_date >= %s ORDER BY snapshot_date, price_brl, store_id",
            (game_id, since_d)).fetchall()
    else:
        rows = conn.execute(
            "SELECT snapshot_date, price_brl, store_id, is_simulated FROM price_snapshots "
            "WHERE game_id = %s AND store_id = %s AND snapshot_date >= %s ORDER BY snapshot_date",
            (game_id, store, since_d)).fetchall()
    pts = [{"date": r["snapshot_date"].isoformat(), "price_brl": db.f(r["price_brl"]), "store_id": r["store_id"],
            "is_simulated": r["is_simulated"]} for r in rows]
    return {"game_id": game_id, "store_id": store, "days": days, "has_simulated": any(p["is_simulated"] for p in pts),
            "points": pts}


@router.get("/api/deals/home", response_model=DealsResponse, tags=["ofertas"])
def deals_home(limit: int = Query(12, ge=1, le=50), conn=Depends(db.get_conn)):
    rows = conn.execute(
        "SELECT * FROM (SELECT DISTINCT ON (l.game_id) l.*, g.slug, g.title FROM v_latest_price l "
        "JOIN games g USING (game_id) WHERE g.tracked AND l.discount_pct > 0 "
        "ORDER BY l.game_id, l.discount_pct DESC, l.price_brl) t ORDER BY discount_pct DESC, price_brl LIMIT %s",
        (limit,)).fetchall()
    meta = mongo_meta([r["game_id"] for r in rows])
    deals = [{"game_id": r["game_id"], "slug": r["slug"], "title": r["title"],
              "thumb": meta.get(r["game_id"], {}).get("background_image"), "offer": pricing.offer_from_row(r)}
             for r in rows]
    return {"count": len(deals), "deals": deals}


@router.get("/api/fx", response_model=FxOut, tags=["câmbio"])
def fx(conn=Depends(db.get_conn)):
    r = conn.execute("SELECT * FROM exchange_rates ORDER BY rate_date DESC LIMIT 1").fetchone()
    if not r:
        raise AppError(404, "not_found", "Sem cotação disponível.")
    return {"rate_date": r["rate_date"].isoformat(), "usd_brl_buy": db.f(r["usd_brl_buy"]),
            "usd_brl_sell": db.f(r["usd_brl_sell"]), "source": r["source"], "fetched_at": r["fetched_at"].isoformat()}

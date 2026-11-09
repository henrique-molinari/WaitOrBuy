"""Ofertas, estatísticas e preço por hora (consultas SQL parametrizadas)."""
from urllib.parse import urlencode

from app.config import VERDICT, settings
from app.db import f, today
from app.services import sales, verdict


def with_affiliate(url: str | None) -> str | None:
    if not url or not settings.affiliate_tag:
        return url
    return url + ("&" if "?" in url else "?") + urlencode({"aff": settings.affiliate_tag})


def offer_from_row(r: dict) -> dict:
    return {
        "store_id": r["store_id"], "store_name": r["store_name"], "price_brl": f(r["price_brl"]),
        "normal_price_brl": f(r["normal_price_brl"]), "discount_pct": f(r["discount_pct"]),
        "price_origin": r["price_origin"], "is_estimated": r["price_origin"] == "converted_usd",
        "deal_url": with_affiliate(r["deal_url"]), "captured_at": r["captured_at"].isoformat(),
    }


def offers_by_game(conn, game_ids: list[int]) -> dict[int, list[dict]]:
    rows = conn.execute(
        "SELECT * FROM v_latest_price WHERE game_id = ANY(%s) ORDER BY price_brl ASC, store_id ASC", (game_ids,)
    ).fetchall()
    out: dict[int, list[dict]] = {gid: [] for gid in game_ids}
    for r in rows:
        out[r["game_id"]].append(offer_from_row(r))
    return out


def price_per_hour(price: float | None, playtime_hours: float | None) -> float | None:
    if price is None or not playtime_hours or playtime_hours <= 0:
        return None
    return round(price / playtime_hours, 2)


def game_stats(conn, game_id: int) -> dict | None:
    r = conn.execute("SELECT * FROM v_price_stats WHERE game_id = %s", (game_id,)).fetchone()
    if not r:
        return None
    sim = conn.execute("SELECT EXISTS (SELECT 1 FROM price_snapshots WHERE game_id = %s AND is_simulated) AS s", (game_id,)).fetchone()["s"]
    return {
        "min_price_brl": f(r["min_price_brl"]), "avg_price_brl": f(r["avg_price_brl"]), "avg_90d_brl": f(r["avg_90d_brl"]),
        "points": r["points"], "first_day": r["first_day"].isoformat(),
        "history_days": (today() - r["first_day"]).days + 1, "has_simulated_history": sim,
    }


def seasonal_rows(conn) -> list[dict]:
    return conn.execute("SELECT * FROM seasonal_sales").fetchall()


def next_sale_info(conn, ref=None) -> dict | None:
    return sales.next_sale(ref or today(), seasonal_rows(conn), ignore=VERDICT.minor_sales)


def build_verdict(best_offer: dict | None, stats: dict | None, sale: dict | None) -> dict:
    return verdict.evaluate(verdict.VerdictInput(
        price_now=best_offer["price_brl"] if best_offer else None,
        min_ever=stats["min_price_brl"] if stats else None,
        avg_all=stats["avg_price_brl"] if stats else None,
        avg_90d=stats["avg_90d_brl"] if stats else None,
        discount_pct=best_offer["discount_pct"] if best_offer else None,
        days_to_next_sale=sale["days"] if sale else None,
        sale_name=sale["name"] if sale else None,
        sale_date=sale["start_date"] if sale else None,
        history_days=stats["history_days"] if stats else 0,
    ))

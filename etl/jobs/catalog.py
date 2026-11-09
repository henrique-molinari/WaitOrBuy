"""Job 3: catálogo. RAWG → MongoDB (waitorbuy.games). Sem RAWG_API_KEY: fixtures rotuladas is_fixture=true."""
import logging
from datetime import datetime, timezone

from etl import config
from etl.clients import rawg
from etl.db import connect, mongo_games
from etl.http import HttpClient
from etl.tracked import load_tracked

log = logging.getLogger("etl.jobs.catalog")


def fixture_doc(game: dict, entry: dict) -> dict:
    app = game["steam_app_id"]
    return {
        "background_image": f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app}/header.jpg" if app else None,
        "genres": entry.get("genres", []), "platforms": ["PC"], "rating": None, "metacritic": None,
        "released": None, "playtime_hours": entry.get("playtime_hours"), "playtime_source": "fixture",
        "description": None, "rawg_id": None, "is_fixture": True,
    }


def rawg_doc(detail: rawg.RawgDetail, entry: dict) -> dict:
    playtime = detail.playtime or None
    source = "rawg"
    if not playtime:
        playtime, source = entry.get("playtime_hours"), "fixture"
    return {
        "background_image": detail.background_image,
        "genres": [g.get("name") for g in detail.genres if g.get("name")],
        "platforms": [p["platform"]["name"] for p in (detail.platforms or []) if p.get("platform")],
        "rating": detail.rating, "metacritic": detail.metacritic, "released": detail.released,
        "playtime_hours": playtime, "playtime_source": source,
        "description": detail.description_raw, "rawg_id": detail.id, "is_fixture": False,
    }


def run(conn=None, http=None, coll=None, api_key: str | None = None) -> dict:
    own = conn is None
    conn = conn or connect()
    coll = coll if coll is not None else mongo_games()
    key = config.RAWG_API_KEY if api_key is None else api_key
    http = http or HttpClient()
    entries = {config.slugify(e["title"]): e for e in load_tracked()}
    coll.create_index("game_id", unique=True)
    stats = {"games": 0, "fixture": 0, "rawg": 0}
    try:
        rows = conn.execute("SELECT game_id, slug, title, steam_app_id FROM games WHERE tracked ORDER BY game_id").fetchall()
        for g in rows:
            entry = entries.get(g["slug"], {})
            doc = None
            if key:
                try:
                    detail = rawg.find_game(http, key, entry.get("search", g["title"]))
                    doc = rawg_doc(detail, entry) if detail else None
                except Exception as exc:
                    log.error("RAWG falhou para %s: %s", g["title"], exc)
            if doc is None:
                doc = fixture_doc(g, entry)
            if doc["rawg_id"]:
                conn.execute("UPDATE games SET rawg_id = %s WHERE game_id = %s", (doc["rawg_id"], g["game_id"]))
            doc.update({"game_id": g["game_id"], "slug": g["slug"], "title": g["title"],
                        "fetched_at": datetime.now(timezone.utc)})
            coll.update_one({"game_id": g["game_id"]}, {"$set": doc}, upsert=True)
            stats["games"] += 1
            stats["fixture" if doc["is_fixture"] else "rawg"] += 1
        conn.commit()
        log.info("catalog: %s", stats)
        return stats
    finally:
        if own:
            conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())

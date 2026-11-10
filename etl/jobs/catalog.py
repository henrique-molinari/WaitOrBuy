"""Job 3: catálogo. RAWG → MongoDB (waitorbuy.games). Sem RAWG_API_KEY: fixtures rotuladas is_fixture=true."""
import logging
from datetime import datetime, timezone

from etl import config
from etl.clients import rawg, steam
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


def steam_doc(meta: dict) -> dict:
    return {
        "background_image": meta.get("background_image"), "genres": meta.get("genres", []),
        "platforms": meta.get("platforms") or ["PC"], "rating": None, "metacritic": meta.get("metacritic"),
        "released": meta.get("released"), "playtime_hours": None, "playtime_source": None,
        "description": meta.get("description"), "rawg_id": None, "is_fixture": False,
    }


def build_doc(game: dict, entry: dict, http, key: str) -> dict:
    """RAWG (com chave) → Steam appdetails (jogos fora do YAML) → fixture editorial (YAML)."""
    if key:
        try:
            detail = rawg.find_game(http, key, entry.get("search", game["title"]))
            if detail:
                return rawg_doc(detail, entry)
        except Exception as exc:
            log.error("RAWG falhou para %s: %s", game["title"], exc)
    if not entry and game["steam_app_id"]:
        try:
            meta = steam.fetch_meta(http, game["steam_app_id"])
            if meta:
                return steam_doc(meta)
        except Exception as exc:
            log.error("Steam appdetails falhou para %s: %s", game["title"], exc)
    return fixture_doc(game, entry)


def save_doc(conn, coll, game: dict, doc: dict) -> None:
    if doc["rawg_id"]:
        conn.execute("UPDATE games SET rawg_id = %s WHERE game_id = %s", (doc["rawg_id"], game["game_id"]))
    doc.update({"game_id": game["game_id"], "slug": game["slug"], "title": game["title"], "fetched_at": datetime.now(timezone.utc)})
    coll.update_one({"game_id": game["game_id"]}, {"$set": doc}, upsert=True)


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
            doc = build_doc(g, entries.get(g["slug"], {}), http, key)
            save_doc(conn, coll, g, doc)
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

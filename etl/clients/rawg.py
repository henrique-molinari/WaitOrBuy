import logging

from pydantic import BaseModel

from etl.http import HttpClient

BASE = "https://api.rawg.io/api"
log = logging.getLogger("etl.rawg")


class RawgDetail(BaseModel):
    id: int
    background_image: str | None = None
    genres: list[dict] = []
    platforms: list[dict] | None = None
    rating: float | None = None
    metacritic: int | None = None
    released: str | None = None
    playtime: int | None = None
    description_raw: str | None = None


def find_game(http: HttpClient, key: str, title: str) -> RawgDetail | None:
    res = http.get_json(f"{BASE}/games", {"search": title, "search_precise": "true", "page_size": 1, "key": key})
    results = (res or {}).get("results") or []
    if not results:
        return None
    detail = http.get_json(f"{BASE}/games/{results[0]['id']}", {"key": key})
    try:
        return RawgDetail.model_validate(detail)
    except Exception as exc:
        log.warning("RAWG detalhe inválido para %s: %s", title, exc)
        return None

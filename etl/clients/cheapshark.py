import logging
from decimal import Decimal

from pydantic import BaseModel, ValidationError

from etl.http import HttpClient

BASE = "https://www.cheapshark.com/api/1.0"
log = logging.getLogger("etl.cheapshark")


class StoreModel(BaseModel):
    storeID: int
    storeName: str
    isActive: int = 1


class SearchHit(BaseModel):
    gameID: str
    steamAppID: str | None = None
    external: str


class Deal(BaseModel):
    storeID: int
    dealID: str
    price: Decimal
    retailPrice: Decimal
    savings: Decimal = Decimal(0)


class GameDetail(BaseModel):
    title: str | None = None
    steam_app_id: int | None = None
    deals: list[Deal] = []


def _validate_list(model, items, what: str):
    out = []
    for it in items or []:
        try:
            out.append(model.model_validate(it))
        except ValidationError as exc:
            log.warning("%s inválido ignorado: %s", what, exc.errors()[:1])
    return out


class CheapSharkClient:
    def __init__(self, http: HttpClient):
        self.http = http

    def stores(self) -> list[StoreModel]:
        return _validate_list(StoreModel, self.http.get_json(f"{BASE}/stores"), "loja")

    def search(self, title: str, limit: int = 10) -> list[SearchHit]:
        return _validate_list(SearchHit, self.http.get_json(f"{BASE}/games", {"title": title, "limit": limit}), "busca")

    def by_steam_app_id(self, app_id: int) -> SearchHit | None:
        """Busca exata pelo app da Steam (mais confiável que o título, que muda entre lojas)."""
        hits = _validate_list(SearchHit, self.http.get_json(f"{BASE}/games", {"steamAppID": app_id}), "busca")
        return hits[0] if hits else None

    def game(self, game_id: str) -> GameDetail:
        data = self.http.get_json(f"{BASE}/games", {"id": game_id})
        info = data.get("info") or {}
        steam = info.get("steamAppID")
        return GameDetail(
            title=info.get("title"),
            steam_app_id=int(steam) if steam and str(steam).isdigit() else None,
            deals=_validate_list(Deal, data.get("deals"), "oferta"),
        )


def deal_url(deal_id: str) -> str:
    return f"https://www.cheapshark.com/redirect?dealID={deal_id}"

import logging
from decimal import Decimal

from pydantic import BaseModel, ValidationError

from etl.http import HttpClient

URL = "https://store.steampowered.com/api/appdetails"
log = logging.getLogger("etl.steam")


class SteamPrice(BaseModel):
    currency: str
    initial: int
    final: int
    discount_percent: int = 0

    @property
    def final_brl(self) -> Decimal:
        return Decimal(self.final) / 100

    @property
    def initial_brl(self) -> Decimal:
        return Decimal(self.initial) / 100


def fetch_price_brl(http: HttpClient, app_id: int) -> SteamPrice | None:
    """Preço real em BRL (centavos → reais). None se jogo grátis/sem preço/erro de formato."""
    data = http.get_json(URL, {"appids": app_id, "cc": "br", "filters": "price_overview"})
    entry = (data or {}).get(str(app_id)) or {}
    payload = entry.get("data")
    if not entry.get("success") or not isinstance(payload, dict) or "price_overview" not in payload:
        return None
    try:
        price = SteamPrice.model_validate(payload["price_overview"])
    except ValidationError as exc:
        log.warning("price_overview inválido para %s: %s", app_id, exc.errors()[:1])
        return None
    return price if price.currency == "BRL" else None

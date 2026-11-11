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


SEARCH_URL = "https://store.steampowered.com/api/storesearch/"
_NOT_A_GAME = ("soundtrack", " ost", "dlc", "season pass", "expansion pass", "artbook", "art book", "wallpaper", "demo", "playtest", "sdk",
               "dedicated server", "character pack", "skin pack", "costume", " vip", " pack", "membership", "upgrade", "bundle", "add-on", " booster",
               "supporter")


def search(http: HttpClient, term: str) -> list[dict]:
    """Busca na loja da Steam (até 10 resultados com preço em BRL). Devolve [{id, name}] só de apps com cara de jogo-base."""
    data = http.get_json(SEARCH_URL, {"term": term, "cc": "br", "l": "english"})
    out = []
    for it in (data or {}).get("items") or []:
        name = it.get("name") or ""
        if it.get("type") != "app" or not it.get("id") or not (it.get("price") or {}).get("final"):
            continue  # pacotes ("sub") e grátis/sem preço não geram oferta
        if any(w in f" {name.lower()}" for w in _NOT_A_GAME):
            continue
        out.append({"id": int(it["id"]), "name": name})
    return out


def fetch_meta(http: HttpClient, app_id: int) -> dict | None:
    """Metadados públicos (nome, capa, gêneros, descrição, lançamento, Metacritic) para jogos fora do YAML."""
    data = http.get_json(URL, {"appids": app_id, "cc": "br", "l": "portuguese"})
    entry = (data or {}).get(str(app_id)) or {}
    d = entry.get("data")
    if not entry.get("success") or not isinstance(d, dict):
        return None
    return {
        "name": d.get("name"), "type": d.get("type"), "background_image": d.get("header_image"),
        "description": d.get("short_description"),
        "genres": [g["description"] for g in d.get("genres", []) if g.get("description")],
        "released": (d.get("release_date") or {}).get("date"),
        "metacritic": (d.get("metacritic") or {}).get("score"),
        "platforms": [n for n, k in (("PC", "windows"), ("Mac", "mac"), ("Linux", "linux")) if (d.get("platforms") or {}).get(k)],
    }

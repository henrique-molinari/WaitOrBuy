"""GOG: busca no catálogo público (catalog.gog.com) e preço em BRL por produto (api.gog.com). Endpoints não oficiais, sem chave.

Falha ou ausência vira "sem preço": o jogo segue com a estimativa da CheapShark.
"""
import logging
import re
from dataclasses import dataclass
from decimal import Decimal

from etl.http import HttpClient
from etl.matching import best_match

CATALOG = "https://catalog.gog.com/v1/catalog"
PRICES = "https://api.gog.com/products/{id}/prices"
PAGE = "https://www.gog.com/pt/game/"
log = logging.getLogger("etl.gog")
_CENTS = re.compile(r"^(\d+) BRL$")


@dataclass(frozen=True)
class GogProduct:
    gog_id: int
    slug: str


def find_product(http: HttpClient, title: str) -> GogProduct | None:
    data = http.get_json(CATALOG, {"query": title, "limit": 10, "order": "desc:score", "productType": "in:game,pack", "page": 1,
                                   "countryCode": "BR", "locale": "en-US", "currencyCode": "BRL"})
    hit = best_match(title, (data or {}).get("products") or [], key=lambda p: p.get("title", ""))
    if not hit or not hit.get("slug"):
        return None
    return GogProduct(int(hit["id"]), hit["slug"])


def search_titles(http: HttpClient, query: str) -> list[str]:
    """Títulos de jogos (não DLC) do catálogo da GOG para a busca."""
    data = http.get_json(CATALOG, {"query": query, "limit": 10, "order": "desc:score", "productType": "in:game", "page": 1,
                                   "countryCode": "BR", "locale": "en-US", "currencyCode": "BRL"})
    return [p["title"] for p in (data or {}).get("products") or [] if p.get("title") and p.get("slug")]


def _cents(v: str | None) -> Decimal | None:
    m = _CENTS.match(v or "")
    return Decimal(m.group(1)) / 100 if m else None


def parse_prices(data: dict) -> tuple[Decimal, Decimal] | None:
    """(preço final, preço normal) em reais; None se não há preço em BRL ou o jogo é grátis."""
    for p in ((data or {}).get("_embedded") or {}).get("prices") or []:
        if (p.get("currency") or {}).get("code") != "BRL":
            continue
        final, base = _cents(p.get("finalPrice")), _cents(p.get("basePrice"))
        if final and final > 0:
            return final.quantize(Decimal("0.01")), max(base or final, final).quantize(Decimal("0.01"))
    return None


def fetch_price(http: HttpClient, gog_id: int) -> tuple[Decimal, Decimal] | None:
    try:
        data = http.get_json(PRICES.format(id=gog_id), {"countryCode": "BR", "currency": "BRL"})
    except RuntimeError as exc:  # 404 (PRICES_NOT_FOUND) chega aqui como erro HTTP depois dos retries
        log.warning("preço GOG %s indisponível: %s", gog_id, exc)
        return None
    return parse_prices(data)


def game_url(slug: str) -> str:
    return PAGE + slug

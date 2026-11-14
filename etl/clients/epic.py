"""Epic Games Store: preço em BRL pelo GraphQL público da própria loja (o mesmo que o site usa; não é uma API oficial documentada).

Sem chave. Pode mudar sem aviso: qualquer falha vira "sem preço" e o jogo segue com a estimativa da CheapShark.
"""
import logging
from dataclasses import dataclass
from decimal import Decimal

from etl.http import HttpClient
from etl.matching import best_match

URL = "https://store.epicgames.com/graphql"
PAGE = "https://store.epicgames.com/pt-BR/p/"
log = logging.getLogger("etl.epic")

QUERY = (
    "query($k:String,$c:String!,$l:String){Catalog{searchStore(keywords:$k,country:$c,locale:$l,count:10,"
    'category:"games/edition/base|bundles/games|editors"){elements{title offerType productSlug '
    "offerMappings{pageSlug pageType} price(country:$c){totalPrice{discountPrice originalPrice currencyCode currencyInfo{decimals}}}}}}}"
)


@dataclass(frozen=True)
class EpicOffer:
    slug: str
    price_brl: Decimal
    normal_brl: Decimal

    @property
    def url(self) -> str:
        return PAGE + self.slug

    @property
    def discount_pct(self) -> float:
        return round(float((1 - self.price_brl / self.normal_brl) * 100), 2) if self.normal_brl > 0 else 0.0


def _slug(el: dict) -> str | None:
    for m in el.get("offerMappings") or []:
        if m.get("pageType") == "productHome" and m.get("pageSlug"):
            return m["pageSlug"]
    return el.get("productSlug") or None


def parse_offer(data: dict, title: str) -> EpicOffer | None:
    """Escolhe o jogo-base que casa com o título e devolve o preço em BRL (None se grátis, sem preço ou outra moeda)."""
    elements = ((((data or {}).get("data") or {}).get("Catalog") or {}).get("searchStore") or {}).get("elements") or []
    base = [e for e in elements if e.get("offerType") in ("BASE_GAME", "BUNDLE", "EDITION")]
    el = best_match(title, base, key=lambda e: e.get("title", ""))
    if not el:
        return None
    tp = (el.get("price") or {}).get("totalPrice") or {}
    slug = _slug(el)
    if not slug or tp.get("currencyCode") != "BRL":
        return None
    scale = Decimal(10) ** int((tp.get("currencyInfo") or {}).get("decimals", 2))
    final, normal = Decimal(tp.get("discountPrice", 0)) / scale, Decimal(tp.get("originalPrice", 0)) / scale
    if final <= 0:
        return None
    return EpicOffer(slug, final.quantize(Decimal("0.01")), max(normal, final).quantize(Decimal("0.01")))


def search_titles(http: HttpClient, query: str) -> list[str]:
    """Títulos de jogos-base que a Epic vende no Brasil para a busca (para descobrir jogos que ainda não conhecemos)."""
    data = http.post_json(URL, {"query": QUERY, "variables": {"k": query, "c": "BR", "l": "en-US"}})
    elements = ((((data or {}).get("data") or {}).get("Catalog") or {}).get("searchStore") or {}).get("elements") or []
    return [e["title"] for e in elements if e.get("offerType") == "BASE_GAME" and e.get("title") and parse_offer(data, e["title"])]


def find_offer(http: HttpClient, title: str) -> EpicOffer | None:
    data = http.post_json(URL, {"query": QUERY, "variables": {"k": title, "c": "BR", "l": "en-US"}})
    if (data or {}).get("errors") and not (data or {}).get("data"):
        raise RuntimeError(f"Epic GraphQL recusou a consulta: {data['errors'][0].get('message')}")
    return parse_offer(data, title)

"""Instant Gaming (loja de chaves): não tem API pública, então usamos só o que o robots.txt permite.

- Descoberta: sitemap oficial (declarado no robots.txt) → índice título normalizado → URL do produto PC.
  A busca interna (/pt/pesquisar/, ?q=) é proibida e NÃO é usada.
- Preço: microdata schema.org (BRL) da página do produto; só vale se o Brasil estiver em `eligibleRegion`.
"""
import logging
import re
from decimal import Decimal

from etl.http import HttpClient

SITEMAP_INDEX = "https://www.instant-gaming.com/sitemap_ig_products_pt{n}.xml"
log = logging.getLogger("etl.instant_gaming")

_LOC = re.compile(r"<loc>https://www\.instant-gaming\.com/pt/(\d+)-comprar-([a-z0-9-]+)/</loc>")
_PLATFORM = re.compile(r"-(pc(?:-mac)?(?:-jogo)?-(?:steam|gog|epic-games|ubisoft-connect|ea-app|battle-net|rockstar|microsoft-store|xbox-game-pass)|pc(?:-jogo)?)$")
_REGION_LOCK = re.compile(r"-(europe|estados-unidos|us|eua|espanha|alemanha|reino-unido|franca|italia|polonia|ásia|asia|canada)(?:-|$)")
_PRICE = re.compile(r'itemprop="priceCurrency"\s+content="([A-Z]{3})"\s*/?>.{0,400}?itemprop="price"\s+content="([0-9.]+)"', re.S)
_AVAILABILITY = re.compile(r'itemprop="availability"\s+content="[^"]*?(InStock|OutOfStock|SoldOut|Discontinued|PreOrder)"')
_REGION = re.compile(r'itemprop="eligibleRegion"\s+content="([A-Z]{2})"')


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def parse_sitemap(xml: str) -> list[dict]:
    """Linhas do índice para produtos de PC sem trava regional. Título = parte do slug antes da plataforma."""
    out = []
    for m in _LOC.finditer(xml):
        ig_id, slug = int(m.group(1)), m.group(2)
        p = _PLATFORM.search(slug)
        if not p or _REGION_LOCK.search(slug[p.start():]):
            continue
        out.append({"ig_id": ig_id, "norm_title": norm(slug[: p.start()]), "platform": p.group(1),
                    "url": f"https://www.instant-gaming.com/pt/{ig_id}-comprar-{slug}/"})
    return out


def fetch_index(http: HttpClient) -> list[dict]:
    rows: list[dict] = []
    for suffix in ("", "_2", "_3", "_4"):
        xml = http.get_text(SITEMAP_INDEX.format(n=suffix))
        if xml is None:  # além da última página
            break
        rows.extend(parse_sitemap(xml))
    return rows


def rank(candidates: list[dict]) -> list[dict]:
    """Candidatos em ordem de preferência: Steam primeiro (o que o público procura), depois a menor id (versão base antes de edições)."""
    return sorted(candidates, key=lambda r: ("steam" not in r["platform"], r["ig_id"]))


def pick_url(candidates: list[dict]) -> str | None:
    ranked = rank(candidates)
    return ranked[0]["url"] if ranked else None


def parse_price_brl(html: str) -> Decimal | None:
    if not html:
        return None
    avail = _AVAILABILITY.search(html)
    if avail and avail.group(1) in ("OutOfStock", "SoldOut", "Discontinued"):
        return None  # sem estoque: o preço mostrado não é uma oferta comprável
    m = _PRICE.search(html)
    if not m or m.group(1) != "BRL":
        return None
    regions = set(_REGION.findall(html))
    if regions and "BR" not in regions:
        return None
    price = Decimal(m.group(2)).quantize(Decimal("0.01"))
    return price if price > 0 else None


def fetch_price_brl(http: HttpClient, url: str) -> Decimal | None:
    return parse_price_brl(http.get_text(url))

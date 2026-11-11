"""Nuuvem (loja brasileira): preço real em BRL lido do microdata schema.org da página do produto.

Só páginas /br-pt/item/<slug> e o sitemap (declarado no robots.txt) são usados; a busca interna é proibida e não é usada.
O slug de cada jogo vem do campo `nuuvem` em tracked_games.yml ou do índice montado a partir do sitemap (`fetch_index`).
"""
import logging
import re
from decimal import Decimal

from etl import config
from etl.http import HttpClient
from etl.matching import best_match, norm

BASE = "https://www.nuuvem.com/br-pt/item/"
SITEMAP = "https://www.nuuvem.com/sitemap.xml"
_SITEMAP_CHILD = re.compile(r"<loc>(https://www\.nuuvem\.com/sitemap\d+\.xml)</loc>")
_ITEM = re.compile(r"<loc>https://www\.nuuvem\.com/br-pt/item/([a-z0-9][a-z0-9-]*)</loc>")
log = logging.getLogger("etl.nuuvem")
_PRICE = re.compile(r'itemprop="priceCurrency"\s+content="([A-Z]{3})"\s*/?>\s*<meta\s+itemprop="price"\s+content="([0-9.]+)"')


def item_url(slug: str) -> str:
    return BASE + slug


def parse_price_brl(html: str) -> Decimal | None:
    m = _PRICE.search(html or "")
    if not m or m.group(1) != "BRL":
        return None
    return Decimal(m.group(2)).quantize(Decimal("0.01"))


def fetch_price_brl(http: HttpClient, slug: str) -> Decimal | None:
    """Preço atual em BRL; None se a página não existe ou não traz oferta."""
    return parse_price_brl(http.get_text(item_url(slug)))


def slug_guesses(title: str) -> list[str]:
    """Slugs prováveis sem usar a busca (proibida): o da Nuuvem costuma ser o título em minúsculas com hífens."""
    cands = [config.slugify(title)]
    if cands[0].startswith("the-"):
        cands.append(cands[0][4:])
    return [c for c in cands if c]


def find_slug(http: HttpClient, title: str) -> str | None:
    """Descobre o slug pelo palpite do título. Só devolve se a página existe E traz preço em BRL; 404 = a loja não vende o jogo."""
    for slug in slug_guesses(title):
        if fetch_price_brl(http, slug) is not None:
            return slug
    return None


def parse_sitemap(xml: str) -> list[str]:
    """Slugs dos produtos da loja brasileira (/br-pt/item/); o sitemap repete cada produto em todos os países, só o BR interessa."""
    return list(dict.fromkeys(_ITEM.findall(xml or "")))


def fetch_index(http: HttpClient) -> list[dict]:
    """Índice [{slug, norm_title}] de todo o catálogo da Nuuvem, lido do sitemap oficial (pesado: ~50 MB, 1x por dia)."""
    root = http.get_text(SITEMAP)
    rows: dict[str, dict] = {}
    for child in _SITEMAP_CHILD.findall(root or ""):
        for slug in parse_sitemap(http.get_text(child)):
            rows.setdefault(slug, {"slug": slug, "norm_title": norm(slug)})
    return list(rows.values())


def pick_slugs(rows: list[dict], title: str, limit: int = 3) -> list[str]:
    """Slugs do índice que são o MESMO jogo (igual ou edição), melhor primeiro: exato, depois o mais curto."""
    ok, pool = [], list(rows)
    while pool and len(ok) < limit:
        hit = best_match(title, pool, key=lambda r: r["norm_title"])
        if not hit:
            break
        ok.append(hit["slug"])
        pool.remove(hit)
    return ok

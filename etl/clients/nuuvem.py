"""Nuuvem (loja brasileira): preço real em BRL lido do microdata schema.org da página do produto.

Só páginas /br-pt/item/<slug> (permitidas pelo robots.txt); a busca interna é proibida e não é usada.
Por isso o slug de cada jogo vem do campo `nuuvem` em tracked_games.yml.
"""
import logging
import re
from decimal import Decimal

from etl import config
from etl.http import HttpClient

BASE = "https://www.nuuvem.com/br-pt/item/"
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


def find_slug(http: HttpClient, title: str) -> str | None:
    """Descobre o slug sem usar a busca (proibida): o da Nuuvem costuma ser o título em minúsculas com hífens.
    Só devolve se a página existe E traz preço em BRL; 404 = a loja não vende o jogo."""
    cands = [config.slugify(title)]
    if cands[0].startswith("the-"):
        cands.append(cands[0][4:])
    for slug in cands:
        if slug and fetch_price_brl(http, slug) is not None:
            return slug
    return None

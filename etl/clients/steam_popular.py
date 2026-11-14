"""Jogos populares da Steam (ids), para o catálogo inicial. Cada fonte é isolada: se uma falha, as outras seguem.

- ISteamChartsService/GetMostPlayedGames: API oficial da Steam, sem chave (top 100 por jogadores simultâneos).
- store.steampowered.com/api/featuredcategories: vitrine da loja (mais vendidos, promoções, lançamentos).
- SteamSpy (top100in2weeks / top100forever): API pública de terceiros; ver docs/REVISAR_JURIDICO.md.
"""
import logging

from etl.http import HttpClient

log = logging.getLogger("etl.steam_popular")
CHARTS = "https://api.steampowered.com/ISteamChartsService/GetMostPlayedGames/v1/"
FEATURED = "https://store.steampowered.com/api/featuredcategories"
STEAMSPY = "https://steamspy.com/api.php"


def _charts(http: HttpClient) -> list[int]:
    data = http.get_json(CHARTS) or {}
    return [int(r["appid"]) for r in (data.get("response") or {}).get("ranks") or [] if r.get("appid")]


def _featured(http: HttpClient) -> list[int]:
    data = http.get_json(FEATURED, {"cc": "br", "l": "english"}) or {}
    out = []
    for key in ("top_sellers", "specials", "new_releases"):
        out += [int(i["id"]) for i in (data.get(key) or {}).get("items") or [] if i.get("id") and i.get("type", 0) == 0]
    return out


def _steamspy(http: HttpClient) -> list[int]:
    """API de terceiros que costuma responder "Too many connections" com status 200 (HTML). Sem retry: insistir só atrasa o ciclo."""
    http = HttpClient(pause=http.pause, retries=0, timeout=10.0)
    out = []
    for req in ("top100in2weeks", "top100forever"):
        data = http.get_json(STEAMSPY, {"request": req}) or {}
        out += [int(k) for k in data if str(k).isdigit()]
    return out


def popular_app_ids(http: HttpClient) -> list[int]:
    """Ids sem repetição, intercalando as fontes (o mais popular de cada uma primeiro)."""
    lists = []
    for name, fetch in (("charts", _charts), ("featured", _featured), ("steamspy", _steamspy)):
        try:
            lists.append(fetch(http))
        except Exception as exc:
            log.warning("fonte de populares %s falhou: %s", name, exc)
    seen, out = set(), []
    for pos in range(max((len(x) for x in lists), default=0)):
        for lst in lists:
            if pos < len(lst) and lst[pos] not in seen:
                seen.add(lst[pos])
                out.append(lst[pos])
    return out

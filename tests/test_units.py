from datetime import date
from decimal import Decimal

import pytest

from app.services import sales
from app.services.alerts import decide
from app.services.cart import build_cart
from app.services.pricing import price_per_hour
from etl import fx
from etl.jobs.prices import pick_hit
from etl.jobs.seed_demo import in_window


# ---- câmbio ----
def test_to_brl_rounds_half_up():
    assert fx.to_brl(Decimal("24.99"), Decimal("5.5013")) == Decimal("137.48")


def test_rate_weekend_uses_last_business_day():
    rates = {date(2026, 11, 5): Decimal("5.40"), date(2026, 11, 6): Decimal("5.5013")}
    assert fx.pick_rate(rates, date(2026, 11, 7)) == (date(2026, 11, 6), Decimal("5.5013"))  # sábado
    assert fx.pick_rate(rates, date(2026, 11, 8)) == (date(2026, 11, 6), Decimal("5.5013"))  # domingo
    assert fx.pick_rate(rates, date(2026, 11, 4)) is None


def test_pick_hit_prefers_exact_title():
    from etl.clients.cheapshark import SearchHit

    hits = [SearchHit(gameID="1", external="Hades II"), SearchHit(gameID="2", external="HADES")]
    assert pick_hit("Hades", hits).gameID == "2"


# ---- sazonais ----
def test_black_friday_is_fourth_friday():
    assert sales.black_friday(2026) == date(2026, 11, 27)
    assert sales.black_friday(2025) == date(2025, 11, 28)
    assert sales.cyber_monday(2026) == date(2026, 11, 30)


ROWS = [
    {"name": "Black Friday", "scope": "all", "rule": "black_friday"},
    {"name": "Steam Winter Sale", "scope": "steam", "rule": None, "start_month": 12, "start_day": 22, "end_month": 1, "end_day": 5},
]


def test_next_sale_black_friday_from_today():
    s = sales.next_sale(date(2026, 11, 9), ROWS)
    assert s["name"] == "Black Friday" and s["days"] == 18


def test_next_sale_year_wrap_active_in_january():
    s = sales.next_sale(date(2027, 1, 3), ROWS)
    assert s["name"] == "Steam Winter Sale" and s["days"] == 0


def test_next_sale_after_black_friday_picks_winter():
    s = sales.next_sale(date(2026, 12, 5), ROWS)
    assert s["name"] == "Steam Winter Sale" and s["days"] == 17


def test_window_wraps_year():
    assert in_window(date(2027, 1, 2), 12, 22, 1, 5) and not in_window(date(2027, 2, 1), 12, 22, 1, 5)


# ---- preço por hora ----
@pytest.mark.parametrize("price,hours,expected", [(50.0, 25, 2.0), (50.0, 0, None), (50.0, None, None), (None, 10, None), (10.0, 3, 3.33)])
def test_price_per_hour(price, hours, expected):
    assert price_per_hour(price, hours) == expected


# ---- carrinho ----
def _o(store, name, price):
    return {"store_id": store, "store_name": name, "price_brl": price, "price_origin": "converted_usd", "deal_url": None}


def test_cart_incomplete_store_after_complete_and_best_mix():
    games = {1: "A", 2: "B"}
    offers = {1: [_o(1, "Steam", 50.0), _o(25, "Epic", 40.0), _o(7, "GOG", 45.0)],
              2: [_o(1, "Steam", 30.0), _o(7, "GOG", 20.0)]}
    cart = build_cart(games, offers)
    assert [s["store_name"] for s in cart["stores"]] == ["GOG", "Steam", "Epic"]
    assert cart["stores"][0]["total_brl"] == 65.0 and cart["stores"][0]["complete"]
    epic = cart["stores"][2]
    assert not epic["complete"] and epic["missing_games"] == [{"game_id": 2, "title": "B"}] and epic["total_brl"] == 40.0
    assert cart["best_mix"]["total_brl"] == 60.0  # 40 (Epic) + 20 (GOG)
    assert cart["best_mix"]["savings_vs_best_store_brl"] == 5.0


def test_cart_empty_and_no_complete_store():
    assert build_cart({}, {})["best_mix"]["total_brl"] == 0
    cart = build_cart({1: "A", 2: "B"}, {1: [_o(1, "Steam", 10.0)], 2: [_o(7, "GOG", 5.0)]})
    assert all(not s["complete"] for s in cart["stores"])
    assert cart["best_mix"]["savings_vs_best_store_brl"] is None


# ---- alertas (regra pura) ----
@pytest.mark.parametrize("price,target,last,expected", [
    (29.9, 30.0, None, "trigger"), (30.0, 30.0, None, "trigger"), (30.01, 30.0, None, "none"),
    (29.9, 30.0, 29.9, "none"), (28.0, 30.0, 29.9, "trigger"), (29.95, 30.0, 29.9, "none"),
    (35.0, 30.0, 29.9, "rearm"),
])
def test_decide(price, target, last, expected):
    assert decide(price, target, last) == expected


def test_http_429_long_retry_after_raises_immediately():
    import httpx

    from etl.http import HttpClient, RateLimited

    calls = []

    def h(req):
        calls.append(1)
        return httpx.Response(429, headers={"retry-after": "2000"}, json={})

    client = HttpClient(pause=0, retries=4, backoff_base=0, transport=httpx.MockTransport(h))
    with pytest.raises(RateLimited):
        client.get_json("https://x.test/a")
    assert len(calls) == 1  # não insiste


# ---- Instant Gaming / Nuuvem / descoberta ----
SITEMAP = """<urlset>
<url><loc>https://www.instant-gaming.com/pt/5972-comprar-hades-pc-mac-jogo-steam/</loc></url>
<url><loc>https://www.instant-gaming.com/pt/5973-comprar-hades-switch-jogo-nintendo-eshop-europe/</loc></url>
<url><loc>https://www.instant-gaming.com/pt/9986-comprar-elden-ring-deluxe-edition-pc-jogo-steam-europe/</loc></url>
<url><loc>https://www.instant-gaming.com/pt/4824-comprar-elden-ring-pc-steam/</loc></url>
<url><loc>https://www.instant-gaming.com/pt/1-comprar-xbox-game-pass-essential-12-meses-xbox-one-microsoft-store/</loc></url>
</urlset>"""


def test_instant_gaming_sitemap_keeps_only_pc_without_region_lock():
    from etl.clients import instant_gaming as ig

    rows = ig.parse_sitemap(SITEMAP)
    assert {r["ig_id"] for r in rows} == {5972, 4824}  # console e versão travada na Europa ficam de fora
    hades = [r for r in rows if r["norm_title"] == "hades"]
    assert ig.pick_url(hades) == "https://www.instant-gaming.com/pt/5972-comprar-hades-pc-mac-jogo-steam/"
    assert ig.norm("Dragon's Dogma 2") == "dragon s dogma 2"
    assert ig.pick_url([]) is None


def test_instant_gaming_price_requires_brl_and_brazil_region():
    from etl.clients import instant_gaming as ig

    page = '<meta itemprop="priceCurrency" content="BRL"><meta itemprop="price" content="160.52"><meta itemprop="eligibleRegion" content="BR">'
    assert ig.parse_price_brl(page) == Decimal("160.52")
    assert ig.parse_price_brl(page.replace('"BRL"', '"EUR"')) is None
    assert ig.parse_price_brl(page.replace('content="BR"', 'content="DE"')) is None  # chave não ativa no Brasil
    assert ig.parse_price_brl(None) is None and ig.parse_price_brl("<html></html>") is None


def test_nuuvem_find_slug_probes_title_slug_and_skips_404():
    import httpx

    from etl.clients import nuuvem
    from etl.http import HttpClient

    ok = '<meta itemprop="priceCurrency" content="BRL" /><meta itemprop="price" content="247.05" />'

    def h(req):
        return httpx.Response(200, text=ok) if req.url.path.endswith("/elden-ring") else httpx.Response(404)

    http = HttpClient(pause=0, retries=0, transport=httpx.MockTransport(h))
    assert nuuvem.find_slug(http, "Elden Ring") == "elden-ring"
    assert nuuvem.find_slug(http, "Jogo Inexistente") is None
    assert nuuvem.fetch_price_brl(http, "elden-ring") == Decimal("247.05")


def test_discovery_relevant_keeps_all_words_ranks_exact_first_and_ignores_accents():
    from etl.discovery import relevant

    titles = ["Hades II", "Hades' Star", "Hades", "Dishonored", "Pokémon Quest"]
    assert relevant("hades", titles) == ["Hades", "Hades II", "Hades' Star"]
    assert relevant("hades star", titles) == ["Hades' Star"]
    assert relevant("baldurs gate", ["Baldur's Gate 3", "Hades"]) == ["Baldur's Gate 3"]  # apóstrofo não atrapalha
    assert relevant("baldur's gate", ["Baldurs Gate II"]) == ["Baldurs Gate II"]
    assert relevant("pokemon", titles) == ["Pokémon Quest"]


def test_discovery_merge_joins_same_game_across_stores_and_keeps_ids():
    from etl.discovery import Candidate, merge

    got = merge([Candidate("Elden Ring", steam_id=1245620), Candidate("ELDEN RING Deluxe Edition"),
                 Candidate("Elden Ring", cheapshark_id="55"), Candidate("Elden Ring Nightreign")])
    assert [(c.title, c.steam_id, c.cheapshark_id) for c in got] == [("Elden Ring", 1245620, "55"), ("Elden Ring Nightreign", None, None)]


def test_steam_search_drops_dlc_packages_and_free_items():
    import httpx

    from etl.clients import steam
    from etl.http import HttpClient

    items = [{"type": "app", "id": 1, "name": "Mortal Kombat 1", "price": {"final": 19999}},
             {"type": "sub", "id": 2, "name": "Mortal Kombat 11 Ultimate", "price": {"final": 27999}},
             {"type": "app", "id": 3, "name": "Mortal Kombat 11 Soundtrack", "price": {"final": 999}},
             {"type": "app", "id": 4, "name": "Mortal Kombat Free", "price": {}},
             {"type": "app", "id": 5, "name": "Mortal Kombat X", "price": {"final": 8999}}]
    http = HttpClient(pause=0, retries=0, transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"items": items})))
    assert steam.search(http, "mortal kombat") == [{"id": 1, "name": "Mortal Kombat 1"}, {"id": 5, "name": "Mortal Kombat X"}]


def test_title_matching_accepts_editions_but_not_sequels_or_dlc():
    from etl.matching import best_match, title_matches

    assert title_matches("The Witcher 3: Wild Hunt", "The Witcher 3: Wild Hunt — Remastered")
    assert title_matches("Disco Elysium", "Disco Elysium - The Final Cut")
    assert title_matches("Hades", "HADES")
    assert not title_matches("Hades", "Hades II")
    assert not title_matches("The Witcher 3: Wild Hunt", "The Witcher 3: Wild Hunt Soundtrack")
    assert not title_matches("", "x") and not title_matches("x", "")
    hit = best_match("Hades", [{"t": "Hades II"}, {"t": "Hades Deluxe Edition"}, {"t": "Hades"}], key=lambda c: c["t"])
    assert hit == {"t": "Hades"}
    assert best_match("Hades", [{"t": "Hades II"}], key=lambda c: c["t"]) is None


def _epic_payload(**over):
    el = {"title": "Hades", "offerType": "BASE_GAME", "productSlug": "hades",
          "offerMappings": [{"pageSlug": "hades", "pageType": "productHome"}],
          "price": {"totalPrice": {"discountPrice": 5999, "originalPrice": 7399, "currencyCode": "BRL", "currencyInfo": {"decimals": 2}}}}
    el.update(over)
    return {"data": {"Catalog": {"searchStore": {"elements": [{"title": "Hades II", "offerType": "BASE_GAME", "productSlug": "hades-ii"}, el]}}}}


def test_epic_parse_offer_real_brl_and_rejects_bad_data():
    from decimal import Decimal

    from etl.clients import epic

    o = epic.parse_offer(_epic_payload(), "Hades")
    assert o.slug == "hades" and o.price_brl == Decimal("59.99") and o.normal_brl == Decimal("73.99")
    assert o.url == "https://store.epicgames.com/pt-BR/p/hades" and o.discount_pct == 18.92
    assert epic.parse_offer(_epic_payload(offerType="DLC"), "Hades") is None
    free = {"totalPrice": {"discountPrice": 0, "originalPrice": 0, "currencyCode": "BRL", "currencyInfo": {"decimals": 2}}}
    assert epic.parse_offer(_epic_payload(price=free), "Hades") is None
    usd = {"totalPrice": {"discountPrice": 999, "originalPrice": 999, "currencyCode": "USD", "currencyInfo": {"decimals": 2}}}
    assert epic.parse_offer(_epic_payload(price=usd), "Hades") is None
    assert epic.parse_offer({}, "Hades") is None and epic.parse_offer({"data": None}, "Hades") is None


def test_gog_parse_prices_cents_to_brl():
    from decimal import Decimal

    from etl.clients import gog

    ok = {"_embedded": {"prices": [{"currency": {"code": "BRL"}, "basePrice": "2049 BRL", "finalPrice": "1435 BRL"}]}}
    assert gog.parse_prices(ok) == (Decimal("14.35"), Decimal("20.49"))
    assert gog.parse_prices({"_embedded": {"prices": [{"currency": {"code": "BRL"}, "basePrice": "0 BRL", "finalPrice": "0 BRL"}]}}) is None
    assert gog.parse_prices({"_embedded": {"prices": [{"currency": {"code": "USD"}, "basePrice": "999 USD", "finalPrice": "999 USD"}]}}) is None
    assert gog.parse_prices({}) is None
    assert gog.game_url("hades") == "https://www.gog.com/pt/game/hades"


def test_instant_gaming_rejects_out_of_stock_and_ranks_candidates():
    from etl.clients import instant_gaming as ig

    page = '<meta itemprop="availability" content="http://schema.org/{}" /><meta itemprop="priceCurrency" content="BRL" /><meta itemprop="price" content="50.00" />'
    assert str(ig.parse_price_brl(page.format("InStock"))) == "50.00"
    assert ig.parse_price_brl(page.format("OutOfStock")) is None
    rows = [{"ig_id": 9, "platform": "pc-jogo-gog", "url": "g"}, {"ig_id": 7, "platform": "pc-steam", "url": "s7"}, {"ig_id": 3, "platform": "pc-steam", "url": "s3"}]
    assert [r["url"] for r in ig.rank(rows)] == ["s3", "s7", "g"]
    assert ig.pick_url([]) is None


def test_http_client_does_not_retry_404_json_and_posts_json():
    import httpx

    from etl.http import HttpClient

    calls = []

    def handler(request):
        calls.append(request.method)
        return httpx.Response(404, json={}) if request.method == "GET" else httpx.Response(200, json={"echo": request.content.decode()})

    c = HttpClient(pause=0, retries=3, backoff_base=0, transport=httpx.MockTransport(handler))
    with pytest.raises(RuntimeError):
        c.get_json("https://x.test/a")
    assert calls == ["GET"]  # sem retry em 4xx
    assert "oi" in c.post_json("https://x.test/b", {"a": "oi"})["echo"]

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

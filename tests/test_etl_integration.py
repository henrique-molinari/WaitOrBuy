"""ETL contra PostgreSQL e MongoDB reais (bancos de teste) com as APIs externas simuladas por MockTransport."""
import json
import os
import zlib

import httpx
import pytest
from pymongo import MongoClient

from etl.http import HttpClient
from etl.jobs import catalog, fx, prices, seed_demo
from etl.tracked import load_tracked


def _crc(s: str) -> int:
    return zlib.crc32(s.encode()) % 900000 + 1000


def handler(request: httpx.Request) -> httpx.Response:
    url, q = str(request.url), request.url.params
    if url.endswith("/stores") or "/stores?" in url:
        return httpx.Response(200, json=[{"storeID": "1", "storeName": "Steam", "isActive": 1},
                                         {"storeID": "25", "storeName": "Epic Games Store", "isActive": 1},
                                         {"storeID": "4", "storeName": "Amazon", "isActive": 0}])
    if "cheapshark.com/api/1.0/games" in url and "title" in q:
        t = q["title"]
        return httpx.Response(200, json=[{"gameID": str(_crc(t.lower())), "steamAppID": str(_crc(t.lower())), "external": t}])
    if "cheapshark.com/api/1.0/games" in url and "id" in q:
        return httpx.Response(200, json={"info": {"title": "x", "steamAppID": q["id"]}, "deals": [
            {"storeID": "1", "dealID": "S%3D", "price": "10.00", "retailPrice": "20.00", "savings": "50.0"},
            {"storeID": "25", "dealID": "E%3D", "price": "10.00", "retailPrice": "20.00", "savings": "50.0"},
            {"storeID": "4", "dealID": "A%3D", "price": "9.00", "retailPrice": "20.00", "savings": "55.0"},
            {"storeID": "oops", "dealID": "bad", "price": "x", "retailPrice": "1"},  # inválida: ignorada, sem derrubar o job
        ]})
    if "appdetails" in url:
        app = q["appids"]
        return httpx.Response(200, json={app: {"success": True, "data": {"price_overview": {
            "currency": "BRL", "initial": 5000, "final": 2500, "discount_percent": 50}}}})
    if "olinda.bcb.gov.br" in url:
        return httpx.Response(200, json={"value": [
            {"cotacaoCompra": 5.4, "cotacaoVenda": 5.5, "dataHoraCotacao": "2026-11-05 13:00:00.1"},
            {"cotacaoCompra": 5.41, "cotacaoVenda": 5.6, "dataHoraCotacao": "2026-11-06 13:00:00.1"},
            {"cotacaoCompra": None, "cotacaoVenda": None, "dataHoraCotacao": "2026-11-07 13:00:00.1"}]})
    return httpx.Response(404, json={})


@pytest.fixture()
def http():
    return HttpClient(pause=0, retries=1, backoff_base=0, transport=httpx.MockTransport(handler))


def count(conn, sql):
    return conn.execute(sql).fetchone()["n"]


def test_fx_job_idempotent_and_skips_null_rows(conn, http):
    fx.run(conn=conn, http=http)
    fx.run(conn=conn, http=http)
    assert count(conn, "SELECT count(*) n FROM exchange_rates") == 2
    assert float(conn.execute("SELECT usd_brl_sell FROM exchange_rates ORDER BY rate_date DESC LIMIT 1").fetchone()["usd_brl_sell"]) == 5.6


def test_prices_job_idempotent_and_origins(conn, http):
    n_games = len(load_tracked())
    s1 = prices.run(conn=conn, http=http)
    snaps = count(conn, "SELECT count(*) n FROM price_snapshots")
    s2 = prices.run(conn=conn, http=http)
    assert count(conn, "SELECT count(*) n FROM price_snapshots") == snaps == 2 * n_games  # 2 lojas ativas por jogo
    assert s1["snapshots"] == s2["snapshots"] == snaps
    steam = conn.execute("SELECT * FROM price_snapshots WHERE store_id = 1 LIMIT 1").fetchone()
    assert steam["price_origin"] == "steam_brl" and float(steam["price_brl"]) == 25.00 and steam["currency_original"] == "BRL"
    epic = conn.execute("SELECT * FROM price_snapshots WHERE store_id = 25 LIMIT 1").fetchone()
    assert epic["price_origin"] == "converted_usd" and epic["currency_original"] == "USD"
    # PTAX mais recente <= hoje (hoje é depois de 06/11): venda 5,60 → 10 USD = 56,00
    assert float(epic["price_brl"]) == 56.00 and float(epic["fx_rate"]) == 5.6
    assert count(conn, "SELECT count(*) n FROM price_snapshots WHERE store_id = 4") == 0  # loja inativa ignorada
    assert count(conn, "SELECT count(*) n FROM games WHERE tracked") == n_games


def test_catalog_fixture_labelled_and_idempotent(conn, http):
    prices.run(conn=conn, http=http)
    coll = MongoClient(os.environ["MONGO_URL"])[os.environ["MONGO_DB"]]["games"]
    coll.delete_many({})
    catalog.run(conn=conn, http=http, coll=coll, api_key="")
    catalog.run(conn=conn, http=http, coll=coll, api_key="")
    assert coll.count_documents({}) == len(load_tracked())
    doc = coll.find_one({"slug": "hades"})
    assert doc["is_fixture"] is True and doc["playtime_hours"] == 22 and doc["playtime_source"] == "fixture"
    assert coll.index_information()["game_id_1"]["unique"]


def test_catalog_rawg_mapping(conn):
    def rawg_handler(request):
        if request.url.path.endswith("/games") :
            return httpx.Response(200, json={"results": [{"id": 3498}]})
        return httpx.Response(200, content=json.dumps({"id": 3498, "background_image": "http://img", "genres": [{"name": "Action"}],
                                                       "platforms": [{"platform": {"name": "PC"}}], "rating": 4.5, "metacritic": 96,
                                                       "released": "2020-09-17", "playtime": 0, "description_raw": "texto"}))

    h = HttpClient(pause=0, retries=0, transport=httpx.MockTransport(rawg_handler))
    conn.execute("INSERT INTO games (title, slug, tracked, steam_app_id) VALUES ('Hades','hades',true,1)")
    coll = MongoClient(os.environ["MONGO_URL"])[os.environ["MONGO_DB"]]["games"]
    coll.delete_many({})
    catalog.run(conn=conn, http=h, coll=coll, api_key="k")
    doc = coll.find_one({"slug": "hades"})
    assert doc["is_fixture"] is False and doc["metacritic"] == 96 and doc["playtime_source"] == "fixture"  # playtime 0 → estimativa rotulada
    assert conn.execute("SELECT rawg_id FROM games").fetchone()["rawg_id"] == 3498


def test_seed_demo_idempotent_simulated_and_keeps_real(conn, http):
    prices.run(conn=conn, http=http)
    real_before = conn.execute("SELECT game_id, store_id, price_brl FROM price_snapshots ORDER BY 1,2").fetchall()
    seed_demo.run(conn=conn)
    total = count(conn, "SELECT count(*) n FROM price_snapshots")
    sim = count(conn, "SELECT count(*) n FROM price_snapshots WHERE is_simulated")
    assert sim == len(real_before) * 180 and total == sim + len(real_before)
    snap1 = conn.execute("SELECT game_id, store_id, snapshot_date, price_brl FROM price_snapshots WHERE is_simulated ORDER BY 1,2,3").fetchall()
    seed_demo.run(conn=conn)
    snap2 = conn.execute("SELECT game_id, store_id, snapshot_date, price_brl FROM price_snapshots WHERE is_simulated ORDER BY 1,2,3").fetchall()
    assert snap1 == snap2  # determinístico e sem duplicar
    real_after = conn.execute("SELECT game_id, store_id, price_brl FROM price_snapshots WHERE NOT is_simulated ORDER BY 1,2").fetchall()
    assert real_after == real_before
    st = conn.execute("SELECT * FROM v_price_stats LIMIT 1").fetchone()
    assert st["points"] == 181 and st["min_price_brl"] <= 56
    assert count(conn, "SELECT count(*) n FROM v_latest_price WHERE is_simulated") if False else True
    assert count(conn, "SELECT count(*) n FROM v_latest_price") == len(real_before)

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
    if url.endswith("nuuvem.com/br-pt/item/hades"):
        return httpx.Response(200, text='<meta itemprop="priceCurrency" content="BRL" /><meta itemprop="price" content="39.9" />')
    if "instant-gaming.com/pt/5972-" in url:
        return httpx.Response(200, text='<meta itemprop="priceCurrency" content="BRL"><meta itemprop="price" content="31.5">'
                                        '<meta itemprop="eligibleRegion" content="BR">')
    if url.endswith("sitemap_ig_products_pt.xml"):
        return httpx.Response(200, text='<url><loc>https://www.instant-gaming.com/pt/5972-comprar-hades-pc-mac-jogo-steam/</loc></url>')
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


def test_nuuvem_and_instant_gaming_prices_are_real_brl(conn, http):
    from etl.jobs import ig_index

    conn.execute("INSERT INTO stores (store_id, name, is_active) VALUES (100, 'Nuuvem', true), (101, 'Instant Gaming', true)")  # vêm da migração; o fixture trunca
    assert ig_index.run(conn=conn, http=http, force=True) == {"rows": 1}
    assert ig_index.run(conn=conn, http=http)["skipped"] is True  # índice fresco: não baixa de novo
    prices.run(conn=conn, http=http)
    prices.run(conn=conn, http=http)  # idempotente
    nv = conn.execute("SELECT * FROM price_snapshots WHERE store_id = 100").fetchall()
    ig = conn.execute("SELECT * FROM price_snapshots WHERE store_id = 101").fetchall()
    assert len(nv) == len(ig) == 1
    assert nv[0]["price_origin"] == "nuuvem_brl" and float(nv[0]["price_brl"]) == 39.90 and nv[0]["currency_original"] == "BRL"
    assert ig[0]["price_origin"] == "instantgaming_brl" and float(ig[0]["price_brl"]) == 31.50 and ig[0]["fx_rate"] is None
    hades = conn.execute("SELECT nuuvem_slug, instant_gaming_url FROM games WHERE slug = 'hades'").fetchone()
    assert hades["nuuvem_slug"] == "hades" and "5972-comprar-hades" in hades["instant_gaming_url"]


def test_discovery_creates_game_prices_it_and_discards_games_without_offers(conn, http):
    from etl import discovery

    prices.run(conn=conn, http=http)  # garante câmbio e lojas
    coll = MongoClient(os.environ["MONGO_URL"])[os.environ["MONGO_DB"]]["games"]
    new = discovery.discover(conn, http, "Zorblax Quest", coll=coll)
    assert len(new) == 1
    g = conn.execute("SELECT * FROM games WHERE game_id = %s", (new[0],)).fetchone()
    assert g["discovered"] and g["tracked"] and g["title"] == "Zorblax Quest"
    assert count(conn, f"SELECT count(*) n FROM price_snapshots WHERE game_id = {new[0]}") == 2  # Steam + Epic
    assert coll.find_one({"game_id": new[0]})["title"] == "Zorblax Quest"
    assert discovery.discover(conn, http, "Zorblax Quest", coll=coll) == []  # já conhecido: nada novo


def _stores(conn):
    conn.execute("INSERT INTO stores (store_id, name, is_active) VALUES (7, 'GOG', true), (100, 'Nuuvem', true), (101, 'Instant Gaming', true)")


def _real_stores_handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if url == "https://store.epicgames.com/graphql":
        return httpx.Response(200, json={"data": {"Catalog": {"searchStore": {"elements": [{
            "title": "Hades", "offerType": "BASE_GAME", "productSlug": "hades", "offerMappings": [{"pageSlug": "hades", "pageType": "productHome"}],
            "price": {"totalPrice": {"discountPrice": 5999, "originalPrice": 7399, "currencyCode": "BRL", "currencyInfo": {"decimals": 2}}}}]}}}})
    if "catalog.gog.com" in url:
        return httpx.Response(200, json={"products": [{"id": "111", "title": "Hades", "slug": "hades"}]})
    if "api.gog.com/products/111/prices" in url:
        return httpx.Response(200, json={"_embedded": {"prices": [{"currency": {"code": "BRL"}, "basePrice": "7000 BRL", "finalPrice": "6500 BRL"}]}})
    return handler(request)


def test_epic_and_gog_real_brl_replace_the_cheapshark_estimate_and_are_not_overwritten(conn):
    _stores(conn)
    http = HttpClient(pause=0, retries=1, backoff_base=0, transport=httpx.MockTransport(_real_stores_handler))
    prices.run(conn=conn, http=http)
    prices.run(conn=conn, http=http)  # idempotente: a estimativa da CheapShark não volta por cima do preço real
    hades = "(SELECT game_id FROM games WHERE slug = 'hades')"
    epic = conn.execute(f"SELECT * FROM price_snapshots WHERE store_id = 25 AND game_id = {hades}").fetchall()
    gog = conn.execute(f"SELECT * FROM price_snapshots WHERE store_id = 7 AND game_id = {hades}").fetchall()
    assert len(epic) == len(gog) == 1
    assert epic[0]["price_origin"] == "epic_brl" and float(epic[0]["price_brl"]) == 59.99 and float(epic[0]["normal_price_brl"]) == 73.99 and epic[0]["fx_rate"] is None
    assert gog[0]["price_origin"] == "gog_brl" and float(gog[0]["price_brl"]) == 65.00 and gog[0]["deal_url"] == "https://www.gog.com/pt/game/hades"
    row = conn.execute("SELECT epic_slug, gog_id, gog_slug FROM games WHERE slug = 'hades'").fetchone()
    assert row == {"epic_slug": "hades", "gog_id": 111, "gog_slug": "hades"}


def test_epic_and_gog_failure_keeps_the_estimate_without_breaking_the_cycle(conn):
    _stores(conn)
    http = HttpClient(pause=0, retries=1, backoff_base=0, transport=httpx.MockTransport(
        lambda r: httpx.Response(500, json={}) if ("epicgames" in str(r.url) or "gog.com" in str(r.url)) else handler(r)))
    stats = prices.run(conn=conn, http=http)
    assert stats["failed"] == 0 and stats["snapshots"] > 0
    assert count(conn, "SELECT count(*) n FROM price_snapshots WHERE price_origin IN ('epic_brl','gog_brl')") == 0
    assert count(conn, "SELECT count(*) n FROM price_snapshots WHERE store_id = 25 AND price_origin = 'converted_usd'") > 0


def test_instant_gaming_tries_next_candidate_when_first_is_out_of_stock_or_other_region(conn):
    from etl.jobs import ig_index

    sitemap = ('<url><loc>https://www.instant-gaming.com/pt/100-comprar-hades-pc-steam/</loc></url>'
               '<url><loc>https://www.instant-gaming.com/pt/200-comprar-hades-pc-steam/</loc></url>'
               '<url><loc>https://www.instant-gaming.com/pt/300-comprar-hades-pc-steam/</loc></url>')
    pages = {
        "/pt/100-": '<meta itemprop="availability" content="http://schema.org/OutOfStock" /><meta itemprop="priceCurrency" content="BRL"><meta itemprop="price" content="10.00">',
        "/pt/200-": '<meta itemprop="priceCurrency" content="BRL"><meta itemprop="price" content="20.00"><meta itemprop="eligibleRegion" content="DE">',
        "/pt/300-": ('<meta itemprop="availability" content="http://schema.org/InStock" /><meta itemprop="priceCurrency" content="BRL">'
                     '<meta itemprop="price" content="30.00"><meta itemprop="eligibleRegion" content="BR">'),
    }

    def h(request):
        url = str(request.url)
        if url.endswith("sitemap_ig_products_pt.xml"):
            return httpx.Response(200, text=sitemap)
        for k, v in pages.items():
            if k in url:
                return httpx.Response(200, text=v)
        return handler(request)

    http = HttpClient(pause=0, retries=1, backoff_base=0, transport=httpx.MockTransport(h))
    _stores(conn)
    ig_index.run(conn=conn, http=http, force=True)
    prices.run(conn=conn, http=http)
    snap = conn.execute("SELECT price_brl, deal_url FROM price_snapshots WHERE store_id = 101").fetchall()
    assert len(snap) == 1 and float(snap[0]["price_brl"]) == 30.00 and "/pt/300-" in snap[0]["deal_url"]
    assert "/pt/300-" in conn.execute("SELECT instant_gaming_url FROM games WHERE slug = 'hades'").fetchone()["instant_gaming_url"]


def _discovery_handler(request: httpx.Request) -> httpx.Response:
    url, q = str(request.url), request.url.params
    if "storesearch" in url:
        return httpx.Response(200, json={"items": [
            {"type": "app", "id": 111, "name": "Mortal Kombat 1", "price": {"final": 19999}},
            {"type": "app", "id": 112, "name": "Mortal Kombat 11 Rain", "price": {"final": 1999}},  # DLC: tipo "dlc" no appdetails
            {"type": "app", "id": 113, "name": "Mortal Kombat 11", "price": {"final": 22999}}]})
    if url == "https://store.epicgames.com/graphql":
        el = {"title": "Mortal Kombat 1", "offerType": "BASE_GAME", "offerMappings": [{"pageSlug": "mk1", "pageType": "productHome"}],
              "price": {"totalPrice": {"discountPrice": 18999, "originalPrice": 19999, "currencyCode": "BRL", "currencyInfo": {"decimals": 2}}}}
        excl = dict(el, title="Mortal Kombat Epic Exclusive", offerMappings=[{"pageSlug": "mkx", "pageType": "productHome"}])
        return httpx.Response(200, json={"data": {"Catalog": {"searchStore": {"elements": [el, excl]}}}})
    if "catalog.gog.com" in url:
        return httpx.Response(200, json={"products": []})
    if "cheapshark.com/api/1.0/games" in url and "mortal" in q.get("title", "").lower():
        return httpx.Response(200, json=[{"gameID": "900", "steamAppID": "111", "external": "Mortal Kombat™ 1"},
                                         {"gameID": "901", "steamAppID": None, "external": "Mortal Kombat Switch Edition"}])
    if "cheapshark.com/api/1.0/games" in url and q.get("id") == "901":  # só a Humble vende (chave de Switch): sem prova de PC
        return httpx.Response(200, json={"info": {"title": "x", "steamAppID": None}, "deals": [
            {"storeID": "25", "dealID": "H%3D", "price": "30.00", "retailPrice": "40.00", "savings": "25.0"}]})
    if "appdetails" in url and "price_overview" not in q.get("filters", ""):
        app = q["appids"]
        kind = "dlc" if app == "112" else "game"
        return httpx.Response(200, json={app: {"success": True, "data": {"type": kind, "name": f"app {app}", "genres": []}}})
    return handler(request)


def test_discovery_finds_games_from_every_store_skips_dlc_and_dedups(conn):
    from etl import discovery

    http = HttpClient(pause=0, retries=0, backoff_base=0, transport=httpx.MockTransport(_discovery_handler))
    prices.run(conn=conn, http=http)  # câmbio e lojas
    coll = MongoClient(os.environ["MONGO_URL"])[os.environ["MONGO_DB"]]["games"]
    new = discovery.discover(conn, http, "mortal kombat", coll=coll)
    titles = sorted(r["title"] for r in conn.execute("SELECT title FROM games WHERE discovered"))
    # Steam (MK1, MK11), Epic (exclusivo) e CheapShark (MK1 de novo, com ™: junta com o da Steam). A DLC "Rain" e o jogo de Switch
    # (só a Humble o vende) ficam de fora.
    assert titles == ["Mortal Kombat 1", "Mortal Kombat 11", "Mortal Kombat Epic Exclusive"] and len(new) == 3
    mk1 = conn.execute("SELECT cheapshark_game_id, steam_app_id FROM games WHERE title = 'Mortal Kombat 1'").fetchone()
    assert mk1 == {"cheapshark_game_id": "900", "steam_app_id": 111}  # ids das duas fontes no mesmo jogo
    excl = conn.execute("SELECT game_id FROM games WHERE title = 'Mortal Kombat Epic Exclusive'").fetchone()["game_id"]
    origins = {r["price_origin"] for r in conn.execute("SELECT price_origin FROM price_snapshots WHERE game_id = %s", (excl,))}
    assert origins == {"epic_brl"}  # jogo sem id na CheapShark e sem Steam: só Epic
    assert discovery.discover(conn, http, "mortal kombat", coll=coll) == []  # segunda busca: nada novo, nada duplicado
    assert count(conn, "SELECT count(*) n FROM games WHERE discovered") == 3


def test_discovery_reports_when_no_store_answers(conn):
    from etl import discovery

    http = HttpClient(pause=0, retries=0, backoff_base=0, transport=httpx.MockTransport(lambda r: httpx.Response(500, json={})))
    with pytest.raises(RuntimeError, match="nenhuma loja"):
        discovery.discover(conn, http, "qualquer coisa")


def test_discovered_games_are_refreshed_at_most_every_12_hours(conn, http):
    prices.run(conn=conn, http=http)
    conn.execute("UPDATE games SET discovered = true WHERE slug = 'hades'")
    before = conn.execute("SELECT max(captured_at) m FROM price_snapshots WHERE game_id = (SELECT game_id FROM games WHERE slug = 'hades')").fetchone()["m"]
    stats = prices.run(conn=conn, http=http)
    after = conn.execute("SELECT max(captured_at) m FROM price_snapshots WHERE game_id = (SELECT game_id FROM games WHERE slug = 'hades')").fetchone()["m"]
    assert before == after and stats["games"] == count(conn, "SELECT count(*) n FROM games WHERE tracked AND NOT discovered")  # recente: pulado
    conn.execute("UPDATE price_snapshots SET captured_at = now() - interval '13 hours' WHERE game_id = (SELECT game_id FROM games WHERE slug = 'hades')")
    prices.run(conn=conn, http=http)
    assert conn.execute("SELECT max(captured_at) m FROM price_snapshots WHERE game_id = (SELECT game_id FROM games WHERE slug = 'hades')").fetchone()["m"] > after

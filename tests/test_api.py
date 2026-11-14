"""Endpoints com PostgreSQL real, MongoDB real e Firebase Emulator (Auth + Firestore)."""
import os

import pytest
from pymongo import MongoClient

from tests.conftest import ADMIN

OFFER_KEYS = {"store_id", "store_name", "price_brl", "normal_price_brl", "discount_pct", "price_origin", "is_estimated",
              "deal_url", "captured_at"}


@pytest.fixture(autouse=True)
def mongo_docs(world):
    coll = MongoClient(os.environ["MONGO_URL"])[os.environ["MONGO_DB"]]["games"]
    coll.delete_many({})
    coll.insert_many([
        {"game_id": 1, "slug": "hades", "title": "Hades", "background_image": "http://img/h", "genres": ["Roguelike"],
         "platforms": ["PC"], "playtime_hours": 20, "is_fixture": True},
        {"game_id": 2, "slug": "celeste", "title": "Celeste", "playtime_hours": 0, "is_fixture": True},
    ])


@pytest.fixture(autouse=True)
def no_live_suggest(monkeypatch):
    """Os testes nunca chamam a Steam de verdade no autocompletar."""
    monkeypatch.setattr("app.routers.search.live_suggestions", lambda *a, **k: [])


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok", "postgres": True, "mongo": True, "firestore": True}


def test_search_sorted_with_origin(client):
    r = client.get("/api/search", params={"q": "had"})
    body = r.json()
    assert r.status_code == 200 and body["count"] == 1
    offers = body["results"][0]["offers"]
    assert [o["price_brl"] for o in offers] == [68.93, 70.0, 73.99]
    assert all(set(o) == OFFER_KEYS for o in offers)
    assert body["results"][0]["best_offer"]["store_name"] == "Epic Games Store"
    assert {o["price_origin"] for o in offers} == {"steam_brl", "converted_usd"}
    assert [o["is_estimated"] for o in offers if o["store_id"] == 1] == [False]


def test_search_validation_and_like_escape(client):
    r = client.get("/api/search", params={"q": "hades", "sort": "nope"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_sort"
    assert client.get("/api/search", params={"q": "%"}).json()["count"] == 0  # % tratado como texto literal
    assert client.get("/api/search", params={"q": "'; DROP TABLE games;--"}).json()["count"] == 0
    assert client.get("/api/search", params={"q": "hades", "limit": 0}).status_code == 422


def test_game_detail_insufficient_without_history(client):
    r = client.get("/api/games/1")
    d = r.json()
    assert r.status_code == 200
    assert d["verdict"]["verdict"] == "INSUFICIENTE" and d["verdict"]["confidence"] == "baixa"
    assert d["playtime_hours"] == 20 and d["price_per_hour"] == round(68.93 / 20, 2)
    assert d["next_sale"]["name"] and d["meta"]["is_fixture"] is True


def test_game_detail_with_history_and_null_playtime(client, add_history):
    add_history(1, 25, 120, 40.0)  # mínimo histórico 40 → preço atual 68,93 muito acima
    d = client.get("/api/games/1").json()
    assert d["stats"]["history_days"] == 121 and d["stats"]["has_simulated_history"] is True
    assert d["verdict"]["confidence"] == "alta" and d["verdict"]["verdict"] in ("ESPERAR", "NEUTRO")
    assert d["verdict"]["metrics"]["min_ever"] == 40.0
    celeste = client.get("/api/games/2").json()
    assert celeste["price_per_hour"] is None  # playtime 0: sem divisão por zero


def test_game_404_and_history(client, add_history):
    r = client.get("/api/games/999")
    assert r.status_code == 404 and r.json() == {"error": {"code": "not_found", "message": "Jogo não encontrado."}}
    add_history(1, 1, 10, 60.0)
    add_history(1, 25, 10, 50.0)
    h = client.get("/api/games/1/history", params={"days": 5}).json()
    assert len(h["points"]) == 6 and h["has_simulated"] and h["points"][0]["price_brl"] == 50.0
    only_steam = client.get("/api/games/1/history", params={"store": 1, "days": 5}).json()
    assert {p["store_id"] for p in only_steam["points"]} == {1}
    assert client.get("/api/games/1/history", params={"days": 5000}).status_code == 422


def test_deals_and_fx(client):
    d = client.get("/api/deals/home").json()
    assert d["count"] == 2 and d["deals"][0]["offer"]["discount_pct"] == 50.0
    fx = client.get("/api/fx").json()
    assert fx["usd_brl_sell"] == 5.5013 and fx["source"] == "BCB PTAX"


def test_auth_required_and_admin_protected(client):
    assert client.get("/api/me/wishlist").status_code == 401
    r = client.get("/api/me/wishlist", headers={"Authorization": "Bearer lixo"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "unauthorized"
    assert client.post("/api/admin/alerts/evaluate").status_code == 403
    assert client.post("/api/admin/alerts/evaluate", headers={"X-Admin-Token": "errado"}).status_code == 403


def test_wishlist_and_cart(client, auth):
    _, h = auth
    assert client.post("/api/me/wishlist", json={"game_id": 999}, headers=h).status_code == 404
    assert client.post("/api/me/wishlist", json={"game_id": "x"}, headers=h).status_code == 422
    for gid in (1, 2, 1):  # repetido é idempotente
        assert client.post("/api/me/wishlist", json={"game_id": gid}, headers=h).status_code == 201
    items = client.get("/api/me/wishlist", headers=h).json()["items"]
    assert sorted(i["game_id"] for i in items) == [1, 2]
    cart = client.get("/api/me/wishlist/cart", headers=h).json()
    assert [s["store_name"] for s in cart["stores"]] == ["Steam", "Epic Games Store", "GOG"]  # Steam única completa
    steam = cart["stores"][0]
    assert steam["complete"] and steam["total_brl"] == 93.99
    epic = cart["stores"][1]
    assert not epic["complete"] and epic["missing_games"][0]["title"] == "Celeste"
    assert cart["best_mix"]["total_brl"] == 88.93 and cart["best_mix"]["savings_vs_best_store_brl"] == 5.06
    assert client.delete("/api/me/wishlist/1", headers=h).json()["removed"] is True
    assert len(client.get("/api/me/wishlist", headers=h).json()["items"]) == 1


def test_users_are_isolated(client, auth):
    _, h1 = auth
    client.post("/api/me/wishlist", json={"game_id": 1}, headers=h1)
    from tests.conftest import httpx, uuid

    host = os.environ["FIREBASE_AUTH_EMULATOR_HOST"]
    t = httpx.post(f"http://{host}/identitytoolkit.googleapis.com/v1/accounts:signUp?key=fake",
                   json={"email": f"{uuid.uuid4().hex[:8]}@t.dev", "password": "senha-123456", "returnSecureToken": True}).json()
    other = {"Authorization": f"Bearer {t['idToken']}"}
    assert client.get("/api/me/wishlist", headers=other).json()["items"] == []


def test_alert_lifecycle_trigger_no_repeat_rearm(client, auth, world):
    uid, h = auth
    c = world["conn"]
    assert client.post("/api/me/alerts", json={"game_id": 1, "target_price_brl": -5}, headers=h).status_code == 422
    assert client.post("/api/me/alerts", json={"game_id": 999, "target_price_brl": 50}, headers=h).status_code == 404
    created = client.post("/api/me/alerts", json={"game_id": 1, "target_price_brl": 60.0}, headers=h)
    assert created.status_code == 201
    alert_id = created.json()["alert_id"]

    def evaluate():
        return client.post("/api/admin/alerts/evaluate", params={"uid": uid}, headers=ADMIN).json()

    def mine(res):  # outros usuários do emulador podem existir; olhamos só a notificação deste usuário
        return client.get("/api/me/notifications", headers=h).json()

    evaluate()  # preço atual 68,93 > alvo 60 → nada
    assert mine(None)["items"] == []
    c.execute("UPDATE price_snapshots SET price_brl = 55.00 WHERE game_id = 1 AND store_id = 25")
    r1 = evaluate()
    n = mine(None)
    assert r1["triggered"] >= 1 and n["unread"] == 1 and "Hades" in n["items"][0]["title"] and n["items"][0]["price_brl"] == 55.0
    evaluate()
    assert len(mine(None)["items"]) == 1, "não deve repetir para o mesmo preço"
    c.execute("UPDATE price_snapshots SET price_brl = 90.00 WHERE game_id = 1 AND store_id = 25")
    c.execute("UPDATE price_snapshots SET price_brl = 90.00 WHERE game_id = 1 AND store_id IN (1, 7)")
    assert evaluate()["rearmed"] >= 1
    alert = client.get("/api/me/alerts", headers=h).json()["items"][0]
    assert alert["last_triggered_price"] is None
    c.execute("UPDATE price_snapshots SET price_brl = 50.00 WHERE game_id = 1 AND store_id = 25")
    evaluate()
    assert len(mine(None)["items"]) == 2, "rearmado: dispara de novo"
    nid = mine(None)["items"][0]["id"]
    assert client.post(f"/api/me/notifications/{nid}/read", headers=h).json()["read"] is True
    assert mine(None)["unread"] == 1
    assert client.post("/api/me/notifications/inexistente/read", headers=h).status_code == 404
    assert client.delete(f"/api/me/alerts/{alert_id}", headers=h).json()["removed"] is True
    assert client.delete(f"/api/me/alerts/{alert_id}", headers=h).status_code == 404


def test_register_device(client, auth):
    _, h = auth
    assert client.post("/api/me/devices", json={"token": "abc/def-0123456789", "platform": "web"}, headers=h).status_code == 201
    assert client.post("/api/me/devices", json={"token": "x"}, headers=h).status_code == 422


def test_rate_limit_returns_429_json(client, monkeypatch):
    import app.main as m

    monkeypatch.setattr(m, "RATE_LIMIT_PER_MIN", 3)
    m._HITS.clear()
    codes = [client.get("/api/fx").status_code for _ in range(5)]
    assert codes[-1] == 429 and codes[0] != 429
    r = client.get("/api/fx")
    assert r.json()["error"]["code"] == "rate_limited"
    m._HITS.clear()


def test_search_filters_sort_and_facets(client):
    allr = client.get("/api/search", params={"q": ""}).json()  # sem termo = navegar o catálogo
    assert allr["count"] == 2 and {f["name"] for f in allr["facets"]} == {"Steam", "Epic Games Store", "GOG"}
    only_gog = client.get("/api/search", params={"q": "hades", "store": 7}).json()
    assert [o["store_name"] for o in only_gog["results"][0]["offers"]] == ["GOG"]
    assert client.get("/api/search", params={"q": "hades", "max_price": 60}).json()["count"] == 0
    assert client.get("/api/search", params={"q": "", "min_discount": 40}).json()["count"] == 2
    assert client.get("/api/search", params={"q": "", "min_discount": 60}).json()["count"] == 0
    by_price = client.get("/api/search", params={"q": "", "sort": "price"}).json()["results"]
    assert [r["title"] for r in by_price] == ["Celeste", "Hades"]  # R$ 20 antes de R$ 68,93
    by_title = client.get("/api/search", params={"q": "", "sort": "title"}).json()["results"]
    assert [r["title"] for r in by_title] == ["Celeste", "Hades"]


def test_suggest_and_platforms(client):
    s = client.get("/api/suggest", params={"q": "ha"}).json()
    assert [x["title"] for x in s["suggestions"]] == ["Hades"]
    p = client.get("/api/platforms").json()
    assert p["count"] == 3 and p["total_games"] == 3
    kinds = {x["name"]: x["price_kind"] for x in p["platforms"]}
    assert kinds == {"Steam": "brl_real", "Epic Games Store": "usd_converted", "GOG": "usd_converted"}
    assert {x["name"] for x in p["providers"]} >= {"CheapShark", "Nuuvem", "Instant Gaming"}


def test_friendly_http_errors_are_portuguese_and_hide_internals(client):
    r = client.get("/api/nao-existe")
    assert r.status_code == 404 and r.json()["error"] == {"code": "not_found", "message": "Não encontramos o que você procurou."}
    r = client.put("/api/search")
    assert r.status_code == 405 and r.json()["error"]["code"] == "method_not_allowed" and "permitida" in r.json()["error"]["message"]
    r = client.get("/api/games/abc")
    assert r.status_code == 422 and r.json()["error"]["message"] == "Entrada inválida em 'path.game_id': precisa ser um número inteiro."
    r = client.get("/api/me/wishlist")
    assert r.status_code == 401 and r.json()["error"]["code"] == "unauthorized"


def test_upstream_failures_become_503_not_500(client, monkeypatch):
    from google.api_core.exceptions import FailedPrecondition
    from pymongo.errors import ServerSelectionTimeoutError

    def boom_mongo(ids):
        raise ServerSelectionTimeoutError("mongo fora")

    monkeypatch.setattr("app.routers.search.mongo_meta", boom_mongo)
    r = client.get("/api/search", params={"q": "had", "live": "false"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "servico_indisponivel"
    assert "mongo" not in r.text.lower() and r.headers["retry-after"] == "30"

    def boom_fs():
        raise FailedPrecondition("The query requires an index")

    monkeypatch.setattr("app.firebase.firestore_client", boom_fs)
    r = client.post("/api/admin/alerts/evaluate", headers=ADMIN)
    assert r.status_code == 503 and "index" not in r.text.lower() and r.json()["error"]["code"] == "servico_indisponivel"


def test_unhandled_error_is_generic_500(client, monkeypatch):
    def boom(ids):
        raise ValueError("segredo interno")

    monkeypatch.setattr("app.routers.search.mongo_meta", boom)
    r = client.get("/api/search", params={"q": "had", "live": "false"})
    assert r.status_code == 500 and "segredo" not in r.text and r.json()["error"]["code"] == "internal_error"


def test_alert_evaluation_falls_back_when_the_collection_group_index_is_missing():
    from google.api_core.exceptions import FailedPrecondition

    from app.services import alerts

    class Doc:
        def __init__(self, active):
            self.active = active

        def to_dict(self):
            return {"active": self.active}

    class Filtered:
        def stream(self):
            raise FailedPrecondition("index required")

    class Group:
        def where(self, **_):
            return Filtered()

        def stream(self):
            return iter([Doc(True), Doc(False), Doc(True)])

    class Fs:
        def collection_group(self, name):
            return Group()

    got = list(alerts._active_alerts(Fs()))
    assert len(got) == 2 and all(d.active for d in got)


def test_suggest_edge_cases_and_platform_kind_reflects_real_origins(client, world):
    assert client.get("/api/suggest", params={"q": "zzzz"}).json()["suggestions"] == []
    assert client.get("/api/suggest", params={"q": "100%_"}).status_code == 200  # curingas do LIKE são escapados
    assert client.get("/api/suggest").status_code == 422
    conn = world["conn"]
    conn.execute("INSERT INTO price_snapshots (game_id, store_id, snapshot_date, price_brl, price_original, currency_original, normal_price_brl, "
                 "discount_pct, deal_url, price_origin) VALUES (2, 7, %s, 30, 30, 'BRL', 30, 0, 'https://gog.test/2', 'gog_brl')", (world["today"],))
    kinds = {x["name"]: x for x in client.get("/api/platforms").json()["platforms"]}
    assert kinds["Steam"]["price_kind"] == "brl_real" and kinds["Epic Games Store"]["price_kind"] == "usd_converted"
    assert kinds["GOG"]["price_kind"] == "mixed" and kinds["GOG"]["source"].startswith("GOG")  # Hades GOG estimado + Celeste GOG real
    assert kinds["Epic Games Store"]["source"].startswith("CheapShark")
    assert {x["name"] for x in client.get("/api/platforms").json()["providers"]} >= {"GOG", "Epic Games Store"}


def test_search_ignores_accents_and_apostrophes(client, world):
    conn = world["conn"]
    conn.execute("INSERT INTO games (title, slug, tracked) VALUES ('Baldur''s Gate 3', 'baldurs-gate-3', true), ('Pokémon Quest', 'pokemon-quest', true)")
    for gid in (4, 5):
        conn.execute("INSERT INTO price_snapshots (game_id, store_id, snapshot_date, price_brl, price_original, currency_original, normal_price_brl, "
                     "discount_pct, deal_url, price_origin) VALUES (%s, 1, %s, 50, 50, 'BRL', 50, 0, 'https://x.test', 'steam_brl')", (gid, world["today"]))
    for q, title in (("baldurs gate", "Baldur's Gate 3"), ("baldur's gate", "Baldur's Gate 3"), ("pokemon", "Pokémon Quest"), ("POKÉMON", "Pokémon Quest")):
        r = client.get("/api/search", params={"q": q, "live": "false"}).json()
        assert [x["title"] for x in r["results"]] == [title], q
    assert [s["title"] for s in client.get("/api/suggest", params={"q": "baldurs"}).json()["suggestions"]] == ["Baldur's Gate 3"]


def test_push_all_sends_with_game_data_and_drops_invalid_devices(monkeypatch):
    from app import firebase
    from app.services import alerts

    devices = {"ok": "tok-ok", "morto": "tok-morto", "falha": "tok-falha"}
    calls = []

    class Dev:
        def __init__(self, key):
            self.id = key
            self.reference = type("R", (), {"delete": staticmethod(lambda: devices.pop(key))})()

        def to_dict(self):
            return {"token": devices[self.id]}

    class Fs:
        def collection(self, _):
            return type("U", (), {"document": lambda s, uid: type("D", (), {"collection": lambda s2, n: type(
                "C", (), {"stream": lambda s3: [Dev(k) for k in list(devices)]})()})()})()

    def fake_send(token, title, body, data=None):
        calls.append((token, data))
        return {"tok-ok": "enviado", "tok-morto": "token_invalido", "tok-falha": "erro"}[token]

    monkeypatch.setattr(firebase, "send_push", fake_send)
    assert alerts.push_all(Fs(), "u1", 7, "Hades chegou ao seu preço", "corpo") is True
    assert set(devices) == {"ok", "falha"}  # só o token inválido foi apagado; a falha passageira fica para a próxima
    assert len(calls) == 3 and all(d["game_id"] == 7 for _, d in calls)
    devices.clear()
    assert alerts.push_all(Fs(), "u1", 7, "t", "b") is False


def test_send_push_maps_fcm_errors(monkeypatch):
    from firebase_admin import messaging

    from app import firebase

    monkeypatch.setattr(firebase, "_init", lambda: None)
    for exc, expected in ((messaging.UnregisteredError("x", None), "token_invalido"), (RuntimeError("rede"), "erro")):
        def boom(msg, _e=exc):
            raise _e
        monkeypatch.setattr(messaging, "send", boom)
        assert firebase.send_push("t", "a", "b") == expected
    monkeypatch.setattr(messaging, "send", lambda msg: "id-1")
    assert firebase.send_push("t", "a", "b", {"game_id": 3}) == "enviado"


def test_search_fuzzy_typo(client):
    """Erro de digitação ainda acha o jogo e avisa que é aproximado."""
    r = client.get("/api/search", params={"q": "hadez", "live": "false"}).json()
    assert r["fuzzy"] is True and r["did_you_mean"] == "Hades" and [g["title"] for g in r["results"]] == ["Hades"]
    r = client.get("/api/search", params={"q": "celest", "live": "false"}).json()  # contido no título: busca exata, sem fuzzy
    assert r["fuzzy"] is False and r["count"] == 1
    r = client.get("/api/search", params={"q": "clesate", "live": "false"}).json()
    assert r["fuzzy"] is True and r["did_you_mean"] == "Celeste"


def test_search_fuzzy_no_noise(client):
    for q in ("zzzzqqq", "??", "ab"):
        r = client.get("/api/search", params={"q": q, "live": "false"}).json()
        assert r["count"] == 0 and r["fuzzy"] is False and r["did_you_mean"] is None


def test_suggest_fuzzy(client):
    assert [s["title"] for s in client.get("/api/suggest", params={"q": "hadez"}).json()["suggestions"]] == ["Hades"]
    assert client.get("/api/suggest", params={"q": "zzzzqqq"}).json()["suggestions"] == []


def test_recommended_excludes_and_has_offer(client):
    r = client.get("/api/recommended", params={"exclude": 1}).json()
    assert r["count"] == len(r["items"]) and all(i["game_id"] != 1 for i in r["items"])
    assert all(i["offer"]["price_brl"] > 0 and i["reason"] in ("genero", "promocao") for i in r["items"])
    assert client.get("/api/recommended", params={"limit": 0}).status_code == 422


def test_suggest_completes_with_live_games(client, monkeypatch):
    calls = []

    def fake(term, known, n):
        calls.append((term, known, n))
        return [{"game_id": None, "slug": None, "title": "Hadestown Quest", "live": True}]

    monkeypatch.setattr("app.routers.search.live_suggestions", fake)
    s = client.get("/api/suggest", params={"q": "had"}).json()["suggestions"]
    assert [(x["title"], x["live"]) for x in s] == [("Hades", False), ("Hadestown Quest", True)] and s[1]["game_id"] is None
    assert calls and calls[0][1] == ["Hades"]
    calls.clear()
    assert [x["live"] for x in client.get("/api/suggest", params={"q": "had", "live": "false"}).json()["suggestions"]] == [False] and not calls
    assert not calls and client.get("/api/suggest", params={"q": "ha"}).status_code == 200  # 2 letras: não consulta a Steam
    assert not [c for c in calls if c[0] == "ha"]


def test_live_suggestions_dedup_cache_and_failure(monkeypatch):
    from app.routers import search

    monkeypatch.undo()  # desfaz o patch automático de live_suggestions: aqui a função real é o alvo
    search._LIVE_SUGGEST.clear()
    n = {"calls": 0}

    def fake_search(http, term):
        n["calls"] += 1
        return [{"id": 1, "name": "Hades"}, {"id": 2, "name": "Hades II"}, {"id": 3, "name": "Hades II"}]

    monkeypatch.setattr("etl.clients.steam.search", fake_search)
    out = search.live_suggestions("hades", ["Hades"], 8)
    assert [o["title"] for o in out] == ["Hades II"] and out[0]["live"] and out[0]["game_id"] is None  # já no banco / duplicado saem
    search.live_suggestions("hades", [], 8)
    assert n["calls"] == 1  # segunda vez vem do cache

    def boom(http, term):
        raise RuntimeError("steam fora")

    search._LIVE_SUGGEST.clear()
    monkeypatch.setattr("etl.clients.steam.search", boom)
    assert search.live_suggestions("hades", [], 8) == []


def test_live_suggestions_drop_dlc_that_extends_a_known_game_but_keep_sequels(monkeypatch):
    from app.routers import search

    monkeypatch.undo()
    search._LIVE_SUGGEST.clear()
    names = [{"id": 1, "name": n} for n in ("Forza Horizon 6 VIP Membership", "Hades II", "Elden Ring Shadow of the Erdtree", "Outro Jogo")]
    monkeypatch.setattr("etl.clients.steam.search", lambda http, term: names)
    out = search.live_suggestions("x", ["Forza Horizon 6", "Hades", "Elden Ring"], 8)
    assert [o["title"] for o in out] == ["Hades II", "Outro Jogo"]

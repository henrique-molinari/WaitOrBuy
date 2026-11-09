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
    r = client.get("/api/search", params={"q": ""})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
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
        return client.post("/api/admin/alerts/evaluate", headers=ADMIN).json()

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

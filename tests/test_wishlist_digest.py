"""E-mail agrupado da wishlist: regra de repetição, texto (sem Firestore) e fluxo completo (com Firestore/Auth Emulator)."""
from datetime import datetime, timedelta, timezone

import pytest

from app.services import wishlist_digest as wd
from tests.conftest import ADMIN

NOW = datetime(2026, 11, 11, tzinfo=timezone.utc)


def test_is_pending_rules():
    assert wd.is_pending(50.0, None, NOW)
    sent = {"price_brl": 50.0, "sent_at": NOW - timedelta(days=2)}
    assert not wd.is_pending(50.0, sent, NOW)           # mesmo preço, aviso recente
    assert not wd.is_pending(52.0, sent, NOW)           # mais caro
    assert wd.is_pending(45.0, sent, NOW)               # preço caiu
    assert wd.is_pending(50.0, {"price_brl": 50.0, "sent_at": NOW - timedelta(days=31)}, NOW)  # aviso antigo


def _item(**kw):
    base = {"game_id": 1, "title": "Hades", "store_id": 1, "store_name": "Steam", "price_brl": 49.9, "is_estimated": False,
            "deal_url": "https://example.test/1", "game_url": "http://site.test/#/jogo/1", "confidence": "alta", "reason": "no menor preço", "based_on_simulated": False}
    return base | kw


def test_render_single_and_many_with_flags():
    one = wd.render_email([_item()])
    assert "Hades" in one["subject"] and "R$ 49,90" in one["body_text"] and "<table" in one["body_html"]
    assert "http://site.test/#/jogo/1" in one["body_html"] and "example.test" not in one["body_html"] + one["body_text"]  # link da plataforma, não da loja
    many = wd.render_email([_item(), _item(game_id=2, title="Celeste <b>", price_brl=20.0, is_estimated=True, based_on_simulated=True)])
    assert "2 jogos" in many["subject"]
    assert "estimado" in many["body_text"] and "simulado" in many["body_text"]
    assert "&lt;b&gt;" in many["body_html"] and "<b>" not in many["body_html"]  # título escapado


@pytest.fixture()
def good_game(world, add_history):
    """Hades com histórico em que o preço atual (68,93, melhor oferta) é o mínimo: veredito COMPRAR_AGORA."""
    add_history(1, 25, 30, 90.0)


def test_full_flow_one_email_per_user_and_no_repeat(client, auth, good_game):
    uid, h = auth
    for gid in (1, 2):  # Celeste não tem histórico: INSUFICIENTE, não entra
        client.post("/api/me/wishlist", json={"game_id": gid}, headers=h)
    r = client.get("/api/admin/wishlist-deals", params={"uid": uid}, headers=ADMIN).json()
    assert r["count"] == 1
    u = r["users"][0]
    assert u["uid"] == uid and "@" in u["email"] and [i["game_id"] for i in u["items"]] == [1]
    assert u["items"][0]["price_brl"] == 68.93 and u["items"][0]["is_estimated"] is True and u["items"][0]["based_on_simulated"] is True
    assert "estimado" in u["body_text"] and "simulado" in u["body_text"]
    import json

    assert json.loads(u["confirm_body"]) == {"uid": uid, "items": [{"game_id": 1, "price_brl": 68.93}]}  # pronto para o POST /sent

    # o GET não grava nada: sem confirmar, continua pendente
    assert client.get("/api/admin/wishlist-deals", params={"uid": uid}, headers=ADMIN).json()["count"] == 1
    sent = client.post("/api/admin/wishlist-deals/sent", json={"uid": uid, "items": [{"game_id": 1, "price_brl": 68.93}]}, headers=ADMIN)
    assert sent.json()["registered"] == 1
    assert client.get("/api/admin/wishlist-deals", params={"uid": uid}, headers=ADMIN).json()["count"] == 0  # não repete


def test_price_drop_after_sent_notifies_again(client, auth, good_game, world):
    uid, h = auth
    client.post("/api/me/wishlist", json={"game_id": 1}, headers=h)
    client.post("/api/admin/wishlist-deals/sent", json={"uid": uid, "items": [{"game_id": 1, "price_brl": 68.93}]}, headers=ADMIN)
    assert client.get("/api/admin/wishlist-deals", params={"uid": uid}, headers=ADMIN).json()["count"] == 0
    world["conn"].execute("UPDATE price_snapshots SET price_brl = 60.00 WHERE game_id = 1 AND store_id = 25 AND snapshot_date = %s", (world["today"],))
    assert client.get("/api/admin/wishlist-deals", params={"uid": uid}, headers=ADMIN).json()["count"] == 1


def test_admin_protected_and_validation(client):
    assert client.get("/api/admin/wishlist-deals").status_code == 403
    assert client.post("/api/admin/wishlist-deals/sent", json={"uid": "x", "items": []}).status_code == 403
    assert client.post("/api/admin/wishlist-deals/sent", json={"uid": "x", "items": []}, headers=ADMIN).status_code == 422

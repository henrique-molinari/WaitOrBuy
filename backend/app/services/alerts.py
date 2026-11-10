"""Avaliação de alertas de preço: dispara, não repete, rearma."""
import logging
from datetime import datetime, timezone

from google.api_core.exceptions import FailedPrecondition
from google.cloud.firestore_v1.base_query import FieldFilter

from app import firebase
from app.services.verdict import brl

log = logging.getLogger("app.alerts")
EPS = 0.005


def decide(price: float, target: float, last_triggered_price: float | None) -> str:
    """'trigger' | 'rearm' | 'none'. Novo preço menor que o último disparado conta como novo disparo."""
    if price <= target:
        if last_triggered_price is None or price < last_triggered_price - EPS:
            return "trigger"
        return "none"
    return "rearm" if last_triggered_price is not None else "none"


def best_price(conn, game_id: int, store_id: int | None) -> dict | None:
    if store_id is None:
        return conn.execute(
            "SELECT store_id, store_name, price_brl FROM v_latest_price WHERE game_id = %s ORDER BY price_brl LIMIT 1",
            (game_id,)).fetchone()
    return conn.execute(
        "SELECT store_id, store_name, price_brl FROM v_latest_price WHERE game_id = %s AND store_id = %s",
        (game_id, store_id)).fetchone()


def _active_alerts(fs):
    """Alertas ativos de todos os usuários. Usa o índice de collection group (firebase/firestore.indexes.json); se ele ainda
    não foi publicado no projeto, lê todos e filtra aqui, para a avaliação nunca parar por falta de índice."""
    group = fs.collection_group("alerts")
    try:
        yield from list(group.where(filter=FieldFilter("active", "==", True)).stream())
    except FailedPrecondition:
        log.warning("índice de collection group 'alerts.active' ausente no Firestore; filtrando em memória (publique firebase/firestore.indexes.json)")
        for doc in group.stream():
            if (doc.to_dict() or {}).get("active"):
                yield doc


def evaluate(conn, fs=None, only_uid: str | None = None) -> dict:
    fs = fs or firebase.firestore_client()
    stats = {"alerts_checked": 0, "triggered": 0, "rearmed": 0, "notifications_created": 0, "push": "nao_configurado"}
    titles = {r["game_id"]: r["title"] for r in conn.execute("SELECT game_id, title FROM games")}
    for doc in _active_alerts(fs):
        if only_uid and doc.reference.parent.parent.id != only_uid:
            continue
        a = doc.to_dict()
        stats["alerts_checked"] += 1
        try:
            offer = best_price(conn, a["game_id"], a.get("store_id"))
            if not offer:
                continue
            price, target = float(offer["price_brl"]), float(a["target_price_brl"])
            action = decide(price, target, a.get("last_triggered_price"))
            if action == "rearm":
                doc.reference.update({"last_triggered_price": None, "last_triggered_at": None})
                stats["rearmed"] += 1
            elif action == "trigger":
                uid = doc.reference.parent.parent.id
                title = titles.get(a["game_id"], f"Jogo {a['game_id']}")
                now = datetime.now(timezone.utc)
                body = f"{title} por {brl(price)} na {offer['store_name']} (alvo {brl(target)})."
                fs.collection("users").document(uid).collection("notifications").add({
                    "title": f"{title} chegou ao seu preço", "body": body, "game_id": a["game_id"],
                    "price_brl": price, "store_id": offer["store_id"], "created_at": now, "read": False,
                })
                doc.reference.update({"last_triggered_price": price, "last_triggered_at": now})
                stats["triggered"] += 1
                stats["notifications_created"] += 1
                if firebase.push_enabled():
                    sent = False
                    for dev in fs.collection("users").document(uid).collection("devices").stream():
                        sent = firebase.send_push(dev.to_dict().get("token", dev.id), f"{title} chegou ao seu preço", body) or sent
                    if sent:
                        stats["push"] = "enviado"
        except Exception as exc:  # um alerta com dado ruim não derruba os demais
            log.error("alerta %s falhou: %s", doc.id, exc)
    return stats

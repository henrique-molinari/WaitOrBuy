from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from google.cloud.firestore_v1 import Query as FsQuery

from app import db, firebase
from app.auth import current_uid
from app.errors import AppError
from app.routers.public import mongo_meta
from app.schemas import AlertCreate, AlertsOut, DeviceIn, NotificationsOut, WishlistAdd, WishlistOut
from app.services import pricing
from app.services.cart import build_cart

router = APIRouter(prefix="/api/me", tags=["usuário"])


def _user(uid: str):
    return firebase.firestore_client().collection("users").document(uid)


def _iso(v) -> str | None:
    return v.isoformat() if v else None


def _game_titles(conn, ids: list[int]) -> dict[int, dict]:
    rows = conn.execute("SELECT game_id, slug, title FROM games WHERE game_id = ANY(%s)", (ids,)).fetchall() if ids else []
    return {r["game_id"]: r for r in rows}


def _require_game(conn, game_id: int) -> None:
    if not conn.execute("SELECT 1 FROM games WHERE game_id = %s", (game_id,)).fetchone():
        raise AppError(404, "not_found", "Jogo não encontrado.")


@router.get("/wishlist", response_model=WishlistOut)
def wishlist(uid: str = Depends(current_uid), conn=Depends(db.get_conn)):
    docs = [d.to_dict() for d in _user(uid).collection("wishlist").stream()]
    ids = [d["game_id"] for d in docs]
    games, offers, meta = _game_titles(conn, ids), pricing.offers_by_game(conn, ids), mongo_meta(ids)
    items = []
    for d in sorted(docs, key=lambda x: x.get("added_at") or datetime.min.replace(tzinfo=timezone.utc), reverse=True):
        g = games.get(d["game_id"])
        if not g:
            continue
        offs = offers.get(d["game_id"], [])
        items.append({"game_id": g["game_id"], "slug": g["slug"], "title": g["title"],
                      "thumb": meta.get(g["game_id"], {}).get("background_image"),
                      "added_at": _iso(d.get("added_at")), "best_offer": offs[0] if offs else None})
    return {"items": items}


@router.post("/wishlist", status_code=201)
def wishlist_add(body: WishlistAdd, uid: str = Depends(current_uid), conn=Depends(db.get_conn)):
    _require_game(conn, body.game_id)
    ref = _user(uid).collection("wishlist").document(str(body.game_id))
    if not ref.get().exists:
        ref.set({"game_id": body.game_id, "added_at": datetime.now(timezone.utc)})
    return {"game_id": body.game_id, "added": True}


@router.delete("/wishlist/{game_id}")
def wishlist_remove(game_id: int, uid: str = Depends(current_uid)):
    _user(uid).collection("wishlist").document(str(game_id)).delete()
    return {"game_id": game_id, "removed": True}


@router.get("/wishlist/cart")
def wishlist_cart(uid: str = Depends(current_uid), conn=Depends(db.get_conn)):
    ids = [d.to_dict()["game_id"] for d in _user(uid).collection("wishlist").stream()]
    games = {gid: g["title"] for gid, g in _game_titles(conn, ids).items()}
    offers = pricing.offers_by_game(conn, list(games))
    return build_cart(games, offers)


def _alert_out(doc, titles: dict[int, dict]) -> dict:
    a = doc.to_dict()
    return {"alert_id": doc.id, "game_id": a["game_id"], "title": titles.get(a["game_id"], {}).get("title", ""),
            "target_price_brl": a["target_price_brl"], "store_id": a.get("store_id"), "active": a.get("active", True),
            "last_triggered_price": a.get("last_triggered_price"), "last_triggered_at": _iso(a.get("last_triggered_at"))}


@router.get("/alerts", response_model=AlertsOut)
def alerts_list(uid: str = Depends(current_uid), conn=Depends(db.get_conn)):
    docs = list(_user(uid).collection("alerts").stream())
    titles = _game_titles(conn, [d.to_dict()["game_id"] for d in docs])
    return {"items": [_alert_out(d, titles) for d in docs]}


@router.post("/alerts", status_code=201)
def alerts_create(body: AlertCreate, uid: str = Depends(current_uid), conn=Depends(db.get_conn)):
    _require_game(conn, body.game_id)
    if body.store_id is not None and not conn.execute("SELECT 1 FROM stores WHERE store_id = %s", (body.store_id,)).fetchone():
        raise AppError(404, "not_found", "Loja não encontrada.")
    ref = _user(uid).collection("alerts").document()
    ref.set({"game_id": body.game_id, "target_price_brl": body.target_price_brl, "store_id": body.store_id,
             "active": True, "last_triggered_price": None, "last_triggered_at": None,
             "created_at": datetime.now(timezone.utc)})
    return _alert_out(ref.get(), _game_titles(conn, [body.game_id]))


@router.delete("/alerts/{alert_id}")
def alerts_delete(alert_id: str, uid: str = Depends(current_uid)):
    ref = _user(uid).collection("alerts").document(alert_id)
    if not ref.get().exists:
        raise AppError(404, "not_found", "Alerta não encontrado.")
    ref.delete()
    return {"alert_id": alert_id, "removed": True}


@router.get("/notifications", response_model=NotificationsOut)
def notifications(limit: int = Query(50, ge=1, le=200), uid: str = Depends(current_uid)):
    col = _user(uid).collection("notifications")
    docs = list(col.order_by("created_at", direction=FsQuery.DESCENDING).limit(limit).stream())
    items = [{"id": d.id, **{k: v for k, v in d.to_dict().items() if k != "created_at"},
              "created_at": _iso(d.to_dict()["created_at"])} for d in docs]
    return {"unread": sum(1 for i in items if not i["read"]), "items": items}


@router.post("/notifications/{notification_id}/read")
def notification_read(notification_id: str, uid: str = Depends(current_uid)):
    ref = _user(uid).collection("notifications").document(notification_id)
    if not ref.get().exists:
        raise AppError(404, "not_found", "Notificação não encontrada.")
    ref.update({"read": True})
    return {"id": notification_id, "read": True}


@router.post("/devices", status_code=201)
def devices(body: DeviceIn, uid: str = Depends(current_uid)):
    # O token FCM vira ID de documento: troca '/' para respeitar o formato de caminho do Firestore.
    _user(uid).collection("devices").document(body.token.replace("/", "_")).set(
        {"token": body.token, "platform": body.platform, "created_at": datetime.now(timezone.utc)})
    return {"registered": True}

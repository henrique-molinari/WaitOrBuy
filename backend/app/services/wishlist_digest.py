"""E-mail único por pessoa com os jogos da wishlist que estão em bom preço (usado pelo workflow KNIME).

"Bom preço" = o veredito "vale esperar?" do jogo é COMPRAR_AGORA (mesma regra da tela do jogo; nada é recalculado aqui).
Não repete: depois que o envio é confirmado, o jogo só volta a entrar se o preço cair abaixo do enviado ou depois de COOLDOWN_DAYS.
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from html import escape

from app import firebase
from app.config import settings
from app.services import pricing
from app.services.verdict import brl

log = logging.getLogger("app.wishlist_digest")
EPS = 0.005
COOLDOWN_DAYS = 30
GOOD = "COMPRAR_AGORA"


def is_pending(price: float, sent: dict | None, now: datetime, cooldown_days: int = COOLDOWN_DAYS) -> bool:
    """True se este jogo ainda deve ser avisado: nunca enviado, preço menor que o enviado, ou aviso antigo."""
    if not sent:
        return True
    if price < float(sent["price_brl"]) - EPS:
        return True
    sent_at = sent.get("sent_at")
    return bool(sent_at and now - sent_at > timedelta(days=cooldown_days))


def render_email(items: list[dict]) -> dict:
    """Assunto, texto e HTML. Estimativa e histórico simulado aparecem sempre sinalizados."""
    n = len(items)
    subject = f"WaitOrBuy: {items[0]['title']} está em bom preço" if n == 1 else f"WaitOrBuy: {n} jogos da sua lista estão em bom preço"
    lines, rows = [], []
    for it in items:
        notes = []
        if it["is_estimated"]:
            notes.append("preço estimado (USD convertido), confirme na loja")
        if it["based_on_simulated"]:
            notes.append("histórico simulado para demonstração")
        note = f" ({'; '.join(notes)})" if notes else ""
        lines.append(f"- {it['title']}: {brl(it['price_brl'])} na {it['store_name']}{note}\n  {it['reason']}\n  Ver na WaitOrBuy: {it['game_url']}")
        link = f'<a href="{escape(it["game_url"], quote=True)}">ver na WaitOrBuy</a>'  # leva à nossa página do jogo, não direto à loja
        rows.append(f"<tr><td>{escape(it['title'])}</td><td>{escape(brl(it['price_brl']))}</td><td>{escape(it['store_name'])}"
                    f"{('<br><small>' + escape('; '.join(notes)) + '</small>') if notes else ''}</td><td>{link}</td></tr>")
    intro = "Um jogo da sua lista de desejos está em um bom preço agora:" if n == 1 else "Estes jogos da sua lista de desejos estão em um bom preço agora:"
    text = f"{intro}\n\n" + "\n\n".join(lines) + "\n\nVocê recebe este aviso porque salvou esses jogos na sua lista no WaitOrBuy."
    html = (f"<p>{intro}</p><table border='1' cellpadding='6' cellspacing='0'><tr><th>Jogo</th><th>Preço</th><th>Loja</th><th></th></tr>"
            f"{''.join(rows)}</table><p><small>Você recebe este aviso porque salvou esses jogos na sua lista no WaitOrBuy.</small></p>")
    return {"subject": subject, "body_text": text, "body_html": html}


def collect(conn, fs=None, only_uid: str | None = None, now: datetime | None = None, cooldown_days: int = COOLDOWN_DAYS,
            email_of=None) -> dict:
    """Usuários com ao menos um jogo em bom preço ainda não avisado, já com o e-mail pronto. Só lê; não grava nada."""
    fs = fs or firebase.firestore_client()
    now = now or datetime.now(timezone.utc)
    email_of = email_of or firebase.user_email
    wished: dict[str, list[int]] = {}
    for doc in fs.collection_group("wishlist").stream():
        uid = doc.reference.parent.parent.id
        if only_uid and uid != only_uid:
            continue
        gid = (doc.to_dict() or {}).get("game_id")
        if gid is not None:
            wished.setdefault(uid, []).append(int(gid))

    game_ids = sorted({g for ids in wished.values() for g in ids})
    titles = {r["game_id"]: r["title"] for r in conn.execute("SELECT game_id, title FROM games WHERE game_id = ANY(%s)", (game_ids,))} if game_ids else {}
    offers = pricing.offers_by_game(conn, game_ids) if game_ids else {}
    sale = pricing.next_sale_info(conn) if game_ids else None
    good: dict[int, dict] = {}
    for gid in game_ids:
        best = (offers.get(gid) or [None])[0]
        if gid not in titles or not best:
            continue
        v = pricing.build_verdict(best, pricing.game_stats(conn, gid), sale)
        if v["verdict"] == GOOD:
            good[gid] = {"game_id": gid, "title": titles[gid], "store_id": best["store_id"], "store_name": best["store_name"],
                         "price_brl": best["price_brl"], "is_estimated": best["is_estimated"], "deal_url": best["deal_url"],
                         "game_url": f"{settings.public_url}/#/jogo/{gid}",
                         "confidence": v["confidence"], "reason": v["reasons"][0], "based_on_simulated": v["based_on_simulated"]}

    users, skipped = [], 0
    for uid, ids in wished.items():
        cands = [good[g] for g in dict.fromkeys(ids) if g in good]
        if not cands:
            continue
        sent = {d.id: d.to_dict() for d in fs.collection("users").document(uid).collection("wishlist_emails").stream()}
        items = sorted((c for c in cands if is_pending(c["price_brl"], sent.get(str(c["game_id"])), now, cooldown_days)), key=lambda c: c["title"])
        if not items:
            continue
        try:
            email = email_of(uid)
        except Exception as exc:  # usuário apagado do Auth ou sem e-mail: pula, não derruba os demais
            log.warning("sem e-mail para %s: %s", uid, type(exc).__name__)
            email = None
        if not email:
            skipped += 1
            continue
        confirm_body = json.dumps({"uid": uid, "items": [{"game_id": i["game_id"], "price_brl": i["price_brl"]} for i in items]})
        users.append({"uid": uid, "email": email, "items": items, **render_email(items), "confirm_body": confirm_body})
    return {"count": len(users), "skipped_without_email": skipped, "users": users}


def confirm(fs, uid: str, items: list[dict], now: datetime | None = None) -> int:
    """Registra o que foi realmente enviado (só chamar depois do e-mail sair). Devolve quantos jogos foram registrados."""
    now = now or datetime.now(timezone.utc)
    col = fs.collection("users").document(uid).collection("wishlist_emails")
    for it in items:
        col.document(str(it["game_id"])).set({"game_id": it["game_id"], "price_brl": it["price_brl"], "sent_at": now})
    return len(items)

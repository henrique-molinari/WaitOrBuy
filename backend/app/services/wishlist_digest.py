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
# Paleta/fontes do app (frontend/src/design/tokens.css), inline porque e-mail não aceita CSS externo nem variáveis.
_SURFACE, _RAISED, _HAIR, _INK, _MUTED = "#f4f0e6", "#fffcf3", "#cdc6b2", "#101512", "#4d554d"
_BUY, _WAIT_TEXT = "#c4f135", "#b3270f"
_DISPLAY = "'Big Shoulders Display','Arial Narrow',Impact,sans-serif"
_SANS = "'Schibsted Grotesk',Helvetica,Arial,sans-serif"
_MONO = "font-family:'Martian Mono','Courier New',monospace;font-weight:500"


def is_pending(price: float, sent: dict | None, now: datetime, cooldown_days: int = COOLDOWN_DAYS) -> bool:
    """True se este jogo ainda deve ser avisado: nunca enviado, preço menor que o enviado, ou aviso antigo."""
    if not sent:
        return True
    if price < float(sent["price_brl"]) - EPS:
        return True
    sent_at = sent.get("sent_at")
    return bool(sent_at and now - sent_at > timedelta(days=cooldown_days))


def render_email(items: list[dict], name: str | None = None) -> dict:
    """Assunto, texto e HTML. Estimativa e histórico simulado aparecem sempre sinalizados."""
    n = len(items)
    first = (name or "").strip().split(" ")[0]  # só o primeiro nome; sem nome na conta, o e-mail segue sem saudação pessoal
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
        link = escape(it["game_url"], quote=True)  # leva à nossa página do jogo, não direto à loja
        note_html = (f'<div style="{_MONO};font-size:11px;line-height:16px;color:{_MUTED};margin-top:10px;">'
                     f'{escape("; ".join(notes))}</div>') if notes else ""
        thumb = it.get("thumb") or ""
        cover = (f'<tr><td colspan="2" style="padding:0;line-height:0;font-size:0;border-bottom:4px solid {_BUY};">'
                 f'<img src="{escape(thumb, quote=True)}" alt="Capa de {escape(it["title"], quote=True)}" width="598" '
                 f'style="display:block;width:100%;height:auto;border:0;"></td></tr>') if thumb.startswith("http") else ""
        rows.append(
            f'<tr><td style="padding:0 0 16px 0;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="background:{_RAISED};border:1px solid {_HAIR};border-radius:12px;overflow:hidden;">{cover}<tr>'
            f'<td style="padding:18px 20px;vertical-align:top;">'
            f'<div style="font-family:{_DISPLAY};font-weight:800;font-size:26px;line-height:28px;color:{_INK};">{escape(it["title"])}</div>'
            f'<div style="{_MONO};font-size:11px;line-height:16px;letter-spacing:.06em;text-transform:uppercase;color:{_MUTED};margin-top:6px;">'
            f'na {escape(it["store_name"])}</div>{note_html}</td>'
            f'<td align="right" style="padding:18px 20px;vertical-align:top;white-space:nowrap;">'
            f'<div style="font-family:{_DISPLAY};font-weight:800;font-size:34px;line-height:34px;color:{_INK};">{escape(brl(it["price_brl"]))}</div>'
            f'<a href="{link}" style="display:inline-block;margin-top:12px;padding:10px 16px;background:{_INK};color:{_SURFACE};'
            f'font-family:{_SANS};font-weight:600;font-size:14px;line-height:16px;text-decoration:none;border-radius:8px;">ver na WaitOrBuy</a>'
            f'</td></tr></table></td></tr>')
    headline = ("Hora de comprar." if n == 1 else f"{n} jogos em bom preço.")
    if first:
        headline = f"{first}, " + (headline[0].lower() + headline[1:])
    greeting = f"Olá, {first}! " if first else ""
    intro = "Um jogo da sua lista de desejos está em um bom preço agora:" if n == 1 else "Estes jogos da sua lista de desejos estão em um bom preço agora:"
    text = f"{greeting}{intro}\n\n" + "\n\n".join(lines) + "\n\nVocê recebe este aviso porque salvou esses jogos na sua lista no WaitOrBuy."
    html = (
        '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<link href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@800&family=Martian+Mono:wght@500&family=Schibsted+Grotesk:wght@400;600&display=swap" rel="stylesheet">'
        f'</head><body style="margin:0;padding:0;background:{_SURFACE};">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{_SURFACE};"><tr><td align="center" style="padding:32px 16px;">'
        f'<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;font-family:{_SANS};color:{_INK};">'
        # marca
        f'<tr><td style="padding:0 0 24px 0;font-family:{_DISPLAY};font-weight:800;font-size:30px;line-height:30px;color:{_INK};">'
        f'Wait<span style="color:{_WAIT_TEXT};font-size:.62em;">or</span><span style="background:{_BUY};padding:0 4px;">Buy</span></td></tr>'
        # cabeçalho
        f'<tr><td style="background:{_INK};border-radius:16px;padding:32px 28px;">'
        f'<div style="display:inline-block;background:{_BUY};color:{_INK};font-family:{_DISPLAY};font-weight:800;font-size:16px;line-height:16px;'
        f'text-transform:uppercase;letter-spacing:.02em;padding:6px 14px;border-radius:999px;">Comprar agora</div>'
        f'<div style="font-family:{_DISPLAY};font-weight:800;font-size:40px;line-height:40px;color:{_SURFACE};margin-top:16px;">{escape(headline)}</div>'
        f'<div style="font-size:16px;line-height:24px;color:{_HAIR};margin-top:12px;">{intro}</div></td></tr>'
        '<tr><td style="height:20px;line-height:20px;font-size:0;">&nbsp;</td></tr>'
        # jogos
        f'<tr><td><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{"".join(rows)}</table></td></tr>'
        # rodapé
        f'<tr><td style="padding:16px 4px 0 4px;{_MONO};font-size:11px;line-height:18px;color:{_MUTED};">'
        'Você recebe este aviso porque salvou esses jogos na sua lista no WaitOrBuy.</td></tr>'
        '</table></td></tr></table></body></html>')
    return {"subject": subject, "body_text": text, "body_html": html}


def collect(conn, fs=None, only_uid: str | None = None, now: datetime | None = None, cooldown_days: int = COOLDOWN_DAYS,
            email_of=None, name_of=None) -> dict:
    """Usuários com ao menos um jogo em bom preço ainda não avisado, já com o e-mail pronto. Só lê; não grava nada."""
    fs = fs or firebase.firestore_client()
    now = now or datetime.now(timezone.utc)
    email_of = email_of or firebase.user_email
    name_of = name_of or firebase.user_name
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
    from app.routers.public import mongo_meta  # capa do jogo; sem Mongo devolve {} e o e-mail sai sem imagem
    covers = mongo_meta(game_ids)
    good: dict[int, dict] = {}
    for gid in game_ids:
        best = (offers.get(gid) or [None])[0]
        if gid not in titles or not best:
            continue
        v = pricing.build_verdict(best, pricing.game_stats(conn, gid), sale)
        if v["verdict"] == GOOD:
            good[gid] = {"game_id": gid, "title": titles[gid], "store_id": best["store_id"], "store_name": best["store_name"],
                         "price_brl": best["price_brl"], "is_estimated": best["is_estimated"], "deal_url": best["deal_url"],
                         "game_url": f"{settings.public_url}/#/jogo/{gid}", "thumb": covers.get(gid, {}).get("background_image"),
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
        try:
            name = name_of(uid)
        except Exception:  # nome é só enfeite: sem ele o e-mail sai sem saudação pessoal
            name = None
        users.append({"uid": uid, "email": email, "items": items, **render_email(items, name), "confirm_body": confirm_body})
    return {"count": len(users), "skipped_without_email": skipped, "users": users}


def confirm(fs, uid: str, items: list[dict], now: datetime | None = None) -> int:
    """Registra o que foi realmente enviado (só chamar depois do e-mail sair). Devolve quantos jogos foram registrados."""
    now = now or datetime.now(timezone.utc)
    col = fs.collection("users").document(uid).collection("wishlist_emails")
    for it in items:
        col.document(str(it["game_id"])).set({"game_id": it["game_id"], "price_brl": it["price_brl"], "sent_at": now})
    return len(items)

"""Fluxo ponta a ponta contra a stack real (API + Postgres + Mongo + Auth/Firestore Emulator).
buscar → lista ordenada → página do jogo → login → wishlist → alerta → avaliação → notificação → marcar lida."""
import os
import sys

import httpx

API = os.getenv("E2E_API", "http://localhost:8000")
AUTH = f"http://{os.environ['FIREBASE_AUTH_EMULATOR_HOST']}/identitytoolkit.googleapis.com/v1/accounts"
ok = True


def check(name: str, cond: bool, extra: str = "") -> None:
    global ok
    ok &= bool(cond)
    print(("OK   " if cond else "FALHA"), name, extra)


c = httpx.Client(base_url=API, timeout=60)
s = c.get("/api/search", params={"q": "hades"}).json()
offers = s["results"][0]["offers"]
check("busca retorna ofertas ordenadas", [o["price_brl"] for o in offers] == sorted(o["price_brl"] for o in offers), f"{len(offers)} ofertas")
check("toda oferta tem price_origin", all(o["price_origin"] in ("steam_brl", "converted_usd") for o in offers))
gid, best = s["results"][0]["game_id"], offers[0]["price_brl"]
g = c.get(f"/api/games/{gid}").json()
check("página do jogo: veredito + histórico", g["verdict"]["verdict"] in ("COMPRAR_AGORA", "ESPERAR", "NEUTRO") and g["stats"]["history_days"] > 90, g["verdict"]["verdict"])
h = c.get(f"/api/games/{gid}/history", params={"days": 90}).json()
check("histórico com selo simulado", h["has_simulated"] and len(h["points"]) > 80, f"{len(h['points'])} pontos")

r = httpx.post(f"{AUTH}:signInWithPassword?key=fake", json={"email": "demo@waitorbuy.test", "password": "demo-123456", "returnSecureToken": True})
check("login demo no emulador", r.status_code == 200)
hd = {"Authorization": f"Bearer {r.json()['idToken']}"}
check("wishlist add", c.post("/api/me/wishlist", json={"game_id": gid}, headers=hd).status_code == 201)
a = c.post("/api/me/alerts", json={"game_id": gid, "target_price_brl": round(best + 10, 2)}, headers=hd)
check("alerta criado", a.status_code == 201)
alert_id = a.json()["alert_id"]
before = c.get("/api/me/notifications", headers=hd).json()["unread"]
ev = c.post("/api/admin/alerts/evaluate", headers={"X-Admin-Token": os.environ["ADMIN_TOKEN"]}).json()
check("avaliação disparou", ev["triggered"] >= 1, str(ev))
n = c.get("/api/me/notifications", headers=hd).json()
check("notificação criada", n["unread"] == before + 1, n["items"][0]["body"])
check("marcar como lida", c.post(f"/api/me/notifications/{n['items'][0]['id']}/read", headers=hd).json()["read"])
fs = f"http://{os.environ['FIRESTORE_EMULATOR_HOST']}/v1/projects/demo-waitorbuy/databases/(default)/documents/users"
uid = r.json()["localId"]
own = httpx.get(f"{fs}/{uid}/notifications", headers={"Authorization": f"Bearer {r.json()['idToken']}"})
check("regras Firestore: usuário lê as próprias notificações (base do listener do front)", own.status_code == 200 and "documents" in own.json())
other = httpx.get(f"{fs}/outro-uid/notifications", headers={"Authorization": f"Bearer {r.json()['idToken']}"})
check("regras Firestore: acesso a dados de outro usuário negado", other.status_code in (401, 403))
cart = c.get("/api/me/wishlist/cart", headers=hd).json()
check("carrinho calculado", cart["game_count"] >= 1 and cart["best_mix"]["total_brl"] > 0)
c.delete(f"/api/me/alerts/{alert_id}", headers=hd)
c.delete(f"/api/me/wishlist/{gid}", headers=hd)
print("E2E", "PASSOU" if ok else "FALHOU")
sys.exit(0 if ok else 1)

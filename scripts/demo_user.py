"""Cria (ou reaproveita) o usuário de demonstração no Auth Emulator (em modo Firebase real não faz nada). Idempotente."""
import os

import httpx

HOST = os.getenv("FIREBASE_AUTH_EMULATOR_HOST")
if not HOST:
    print("Modo Firebase real: nenhum usuário de demonstração é criado automaticamente. Crie a conta pela tela de cadastro.")
    raise SystemExit(0)
EMAIL, PASSWORD = "demo@waitorbuy.test", "demo-123456"
base = f"http://{HOST}/identitytoolkit.googleapis.com/v1/accounts"
r = httpx.post(f"{base}:signUp?key=fake", json={"email": EMAIL, "password": PASSWORD, "returnSecureToken": True})
if r.status_code != 200:  # já existe
    r = httpx.post(f"{base}:signInWithPassword?key=fake", json={"email": EMAIL, "password": PASSWORD, "returnSecureToken": True})
    r.raise_for_status()
print(f"usuário de demonstração pronto: {EMAIL} / {PASSWORD} (uid {r.json()['localId']})")

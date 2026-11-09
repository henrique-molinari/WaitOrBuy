import secrets

from app import firebase
from app.config import settings
from app.errors import AppError
from fastapi import Header


def current_uid(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(401, "unauthorized", "Token de autenticação ausente.")
    token = authorization[7:].strip()
    try:
        claims = firebase.verify_token(token)
    except Exception:
        raise AppError(401, "unauthorized", "Token inválido ou expirado.") from None
    uid = claims.get("uid") or claims.get("user_id") or claims.get("sub")
    if not uid:
        raise AppError(401, "unauthorized", "Token sem identificação de usuário.")
    return uid


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    expected = settings.admin_token
    if not expected or not x_admin_token or not secrets.compare_digest(x_admin_token, expected):
        raise AppError(403, "forbidden", "Token administrativo inválido.")

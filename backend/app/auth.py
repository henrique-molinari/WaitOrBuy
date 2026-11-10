import secrets

from fastapi import Header

from app import firebase
from app.config import settings
from app.errors import AppError


def current_uid(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(401, "unauthorized", "Você precisa entrar na sua conta para fazer isso.")
    token = authorization[7:].strip()
    try:
        claims = firebase.verify_token(token)
    except Exception:
        raise AppError(401, "unauthorized", "Sua sessão expirou ou é inválida. Entre novamente.") from None
    uid = claims.get("uid") or claims.get("user_id") or claims.get("sub")
    if not uid:
        raise AppError(401, "unauthorized", "Não foi possível identificar sua conta. Entre novamente.")
    return uid


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    expected = settings.admin_token
    if not expected or not x_admin_token or not secrets.compare_digest(x_admin_token, expected):
        raise AppError(403, "forbidden", "Você não tem permissão para fazer isso.")

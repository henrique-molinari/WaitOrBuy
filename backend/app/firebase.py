"""Firebase Admin: validação de token (Auth) e Firestore. Em dev usa os emuladores via variáveis de ambiente."""
import os

import firebase_admin
from firebase_admin import auth, credentials

from app.config import settings

_fs = None


def _init() -> None:
    if firebase_admin._apps:
        return
    if settings.firebase_credentials:
        firebase_admin.initialize_app(credentials.Certificate(settings.firebase_credentials), {"projectId": settings.project_id})
    else:
        firebase_admin.initialize_app(options={"projectId": settings.project_id})


def firestore_client():
    global _fs
    if _fs is None:
        _init()
        if os.getenv("FIRESTORE_EMULATOR_HOST") and not settings.firebase_credentials:
            from google.auth.credentials import AnonymousCredentials
            from google.cloud import firestore

            _fs = firestore.Client(project=settings.project_id, credentials=AnonymousCredentials())
        else:
            from firebase_admin import firestore

            _fs = firestore.client()
    return _fs


def verify_token(token: str) -> dict:
    _init()
    return auth.verify_id_token(token)


def user_email(uid: str) -> str | None:
    """E-mail da conta no Firebase Auth (None se a conta não tiver)."""
    _init()
    return auth.get_user(uid).email


def push_enabled() -> bool:
    return bool(settings.firebase_credentials)


def send_push(token: str, title: str, body: str, data: dict | None = None) -> str:
    """Envia FCM. Só chamado quando FIREBASE_CREDENTIALS está configurado.
    Devolve 'enviado', 'token_invalido' (o dispositivo não existe mais: quem chamou deve apagá-lo) ou 'erro' (falha passageira)."""
    import logging

    from firebase_admin import exceptions, messaging

    _init()
    try:
        messaging.send(messaging.Message(token=token, notification=messaging.Notification(title=title, body=body),
                                         data={k: str(v) for k, v in (data or {}).items()}))
        return "enviado"
    except (messaging.UnregisteredError, messaging.SenderIdMismatchError):
        return "token_invalido"
    except exceptions.InvalidArgumentError:
        return "token_invalido"
    except Exception as exc:
        logging.getLogger("app.push").warning("push FCM falhou: %s", exc)
        return "erro"

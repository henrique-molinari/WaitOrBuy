"""Erros padronizados: {"error": {"code", "message"}}."""
import logging
from http import HTTPStatus

import psycopg
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from google.api_core.exceptions import GoogleAPICallError
from pymongo.errors import PyMongoError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("app.errors")

CODES = {400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found", 405: "method_not_allowed", 409: "conflict",
         413: "payload_too_large", 422: "validation_error", 429: "rate_limited", 503: "servico_indisponivel"}
# Mensagens amigáveis (português) para os erros que o framework gera sozinho, no lugar do texto em inglês.
FRIENDLY = {
    400: "Requisição inválida. Confira os dados enviados.",
    401: "Você precisa entrar na sua conta para fazer isso.",
    403: "Você não tem permissão para fazer isso.",
    404: "Não encontramos o que você procurou.",
    405: "Esta operação não é permitida neste endereço.",
    409: "Esta ação conflita com o estado atual. Atualize a página e tente de novo.",
    413: "O conteúdo enviado é grande demais.",
    429: "Muitas requisições; tente novamente em instantes.",
    503: "Alguns serviços estão fora do ar agora. Tente novamente em instantes.",
}
UNAVAILABLE_MSG = "Alguns serviços estão fora do ar agora. Tente novamente em instantes."


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


VALIDATION_PT = {
    "missing": "campo obrigatório", "int_parsing": "precisa ser um número inteiro", "float_parsing": "precisa ser um número",
    "string_too_long": "texto longo demais", "string_too_short": "texto curto demais", "greater_than": "valor baixo demais",
    "greater_than_equal": "valor baixo demais", "less_than": "valor alto demais", "less_than_equal": "valor alto demais",
    "json_invalid": "JSON inválido", "bool_parsing": "precisa ser verdadeiro ou falso",
}


def _body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def install(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(_body(exc.code, exc.message), status_code=exc.status)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        detail = str(exc.detail)
        # Starlette usa a frase HTTP em inglês ("Not Found") quando ninguém escreveu uma mensagem: troca pela amigável.
        if detail == HTTPStatus(exc.status_code).phrase and exc.status_code in FRIENDLY:
            detail = FRIENDLY[exc.status_code]
        elif exc.status_code >= 500:
            detail = FRIENDLY.get(exc.status_code, "Erro interno do servidor.")
        return JSONResponse(_body(CODES.get(exc.status_code, "http_error"), detail), status_code=exc.status_code, headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        return JSONResponse(_body("validation_error", f"Entrada inválida em '{loc}': {VALIDATION_PT.get(first.get('type', ''), 'valor não aceito')}."), status_code=422)

    @app.exception_handler(GoogleAPICallError)
    async def _firestore_down(_: Request, exc: GoogleAPICallError):
        log.error("serviço do Google indisponível ou recusou a consulta: %s", exc)
        return JSONResponse(_body("servico_indisponivel", UNAVAILABLE_MSG), status_code=503, headers={"Retry-After": "30"})

    @app.exception_handler(psycopg.OperationalError)
    async def _postgres_down(_: Request, exc: psycopg.OperationalError):
        log.error("PostgreSQL indisponível: %s", exc)
        return JSONResponse(_body("servico_indisponivel", UNAVAILABLE_MSG), status_code=503, headers={"Retry-After": "30"})

    @app.exception_handler(PyMongoError)
    async def _mongo_down(_: Request, exc: PyMongoError):
        log.error("MongoDB indisponível: %s", exc)
        return JSONResponse(_body("servico_indisponivel", UNAVAILABLE_MSG), status_code=503, headers={"Retry-After": "30"})

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        log.exception("erro não tratado: %s", exc)
        return JSONResponse(_body("internal_error", "Algo deu errado do nosso lado. Tente novamente em instantes."), status_code=500)

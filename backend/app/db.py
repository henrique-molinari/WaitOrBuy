"""Acesso aos bancos: PostgreSQL (psycopg 3, SQL parametrizado) e MongoDB."""
from datetime import datetime
from decimal import Decimal

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pymongo import MongoClient

from app.config import TZ, settings

_pool: ConnectionPool | None = None
_mongo: MongoClient | None = None


def pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            settings.database_url, min_size=1, max_size=8, open=True,
            kwargs={"row_factory": dict_row, "options": "-c timezone=America/Sao_Paulo"},
        )
    return _pool


def get_conn():
    """Dependência FastAPI: uma conexão do pool por requisição."""
    with pool().connection() as conn:
        yield conn


def mongo_games():
    global _mongo
    if _mongo is None:
        _mongo = MongoClient(settings.mongo_url, serverSelectionTimeoutMS=3000)
    return _mongo[settings.mongo_db]["games"]


def today():
    return datetime.now(TZ).date()


def f(x) -> float | None:
    """Decimal → float (JSON numérico), preservando None."""
    return None if x is None else float(x) if isinstance(x, Decimal) else x

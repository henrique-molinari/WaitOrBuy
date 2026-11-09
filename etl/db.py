import psycopg
from psycopg.rows import dict_row

from etl import config


def connect(url: str | None = None) -> psycopg.Connection:
    return psycopg.connect(url or config.DATABASE_URL, row_factory=dict_row, options="-c timezone=America/Sao_Paulo")


def mongo_games():
    from pymongo import MongoClient

    client = MongoClient(config.MONGO_URL, serverSelectionTimeoutMS=5000)
    return client[config.MONGO_DB]["games"]

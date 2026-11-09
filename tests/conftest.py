"""Fixtures: banco PostgreSQL e Mongo de TESTE reais (waitorbuy_test) + Firebase Emulator."""
import os
import uuid
from datetime import timedelta

import httpx
import psycopg
import pytest
from psycopg.rows import dict_row

ADMIN_URL = os.environ["DATABASE_URL"]
TEST_DB = "waitorbuy_test"
TEST_URL = ADMIN_URL.rsplit("/", 1)[0] + "/" + TEST_DB
# Deve vir antes de importar etl.* e app.*, que leem o ambiente na importação.
os.environ["DATABASE_URL"] = TEST_URL
os.environ["MONGO_DB"] = TEST_DB
os.environ["ADMIN_TOKEN"] = "token-de-teste"
os.environ["ETL_PAUSE_SECONDS"] = "0"
os.environ["AFFILIATE_TAG"] = ""


@pytest.fixture(scope="session", autouse=True)
def testdb():
    with psycopg.connect(ADMIN_URL.rsplit("/", 1)[0] + "/postgres", autocommit=True) as c:
        c.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
        c.execute(f"CREATE DATABASE {TEST_DB}")
    from etl import migrate

    migrate.run()
    yield
    from pymongo import MongoClient

    MongoClient(os.environ["MONGO_URL"]).drop_database(TEST_DB)


@pytest.fixture()
def conn():
    with psycopg.connect(TEST_URL, row_factory=dict_row, autocommit=True) as c:
        c.execute("TRUNCATE price_snapshots, games, stores, exchange_rates RESTART IDENTITY CASCADE")
        yield c


@pytest.fixture()
def world(conn):
    """3 jogos, 3 lojas. Hades (id 1): Steam 73,99 BRL real + Epic 68,93 estimado + GOG 70,00.
    Celeste (id 2): só Steam 20,00 (deixa Epic/GOG incompletas no carrinho). Sem histórico além de hoje."""
    from etl import config

    today = config.today_br()
    conn.execute("INSERT INTO stores (store_id, name) VALUES (1,'Steam'),(7,'GOG'),(25,'Epic Games Store')")
    conn.execute("INSERT INTO games (title, slug, tracked, steam_app_id) VALUES ('Hades','hades',true,1145360),"
                 "('Celeste','celeste',true,504230),('Zero Hora','zero-hora',true,null)")
    conn.execute("INSERT INTO exchange_rates (rate_date, usd_brl_buy, usd_brl_sell) VALUES (%s, 5.5, 5.5013)", (today,))
    rows = [(1, 1, 73.99, 'steam_brl'), (1, 25, 68.93, 'converted_usd'), (1, 7, 70.00, 'converted_usd'),
            (2, 1, 20.00, 'steam_brl')]
    for g, s, p, o in rows:
        conn.execute(
            "INSERT INTO price_snapshots (game_id, store_id, snapshot_date, price_brl, price_original, currency_original, "
            "normal_price_brl, discount_pct, deal_url, price_origin) VALUES (%s,%s,%s,%s,%s,'BRL',%s,%s,%s,%s)",
            (g, s, today, p, p, p * 2, 50, f"https://example.test/{g}/{s}", o))
    return {"today": today, "conn": conn}


@pytest.fixture()
def add_history(world):
    def _add(game_id: int, store_id: int, days: int, price: float):
        for back in range(1, days + 1):
            world["conn"].execute(
                "INSERT INTO price_snapshots (game_id, store_id, snapshot_date, price_brl, price_original, currency_original, "
                "price_origin, is_simulated) VALUES (%s,%s,%s,%s,%s,'BRL','steam_brl',true) ON CONFLICT DO NOTHING",
                (game_id, store_id, world["today"] - timedelta(days=back), price, price))
    return _add


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture()
def auth():
    """Cria um usuário novo no Auth Emulator e devolve (uid, headers)."""
    host = os.environ["FIREBASE_AUTH_EMULATOR_HOST"]
    r = httpx.post(f"http://{host}/identitytoolkit.googleapis.com/v1/accounts:signUp?key=fake",
                   json={"email": f"{uuid.uuid4().hex[:10]}@teste.dev", "password": "senha-123456", "returnSecureToken": True})
    r.raise_for_status()
    d = r.json()
    return d["localId"], {"Authorization": f"Bearer {d['idToken']}"}


ADMIN = {"X-Admin-Token": "token-de-teste"}

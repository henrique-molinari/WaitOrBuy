"""Configuração do ETL via variáveis de ambiente."""
import os
import re
import unicodedata
from datetime import date, datetime
from zoneinfo import ZoneInfo

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://waitorbuy:waitorbuy@localhost:5432/waitorbuy")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "waitorbuy")
RAWG_API_KEY = os.getenv("RAWG_API_KEY", "").strip()
USER_AGENT = os.getenv("ETL_USER_AGENT", "WaitOrBuy-Academic/0.1 (student project)")
PAUSE_SECONDS = float(os.getenv("ETL_PAUSE_SECONDS", "1.5"))
INTERVAL_HOURS = float(os.getenv("ETL_INTERVAL_HOURS", "4"))
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
TZ = ZoneInfo("America/Sao_Paulo")


def today_br() -> date:
    return datetime.now(TZ).date()


def slugify(title: str) -> str:
    s = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

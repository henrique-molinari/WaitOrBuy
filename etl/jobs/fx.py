"""Job 2: cotação PTAX (venda/compra) do Banco Central → exchange_rates (upsert por data)."""
import logging
import os
from datetime import timedelta

from etl import config
from etl.clients import ptax
from etl.db import connect
from etl.http import HttpClient

log = logging.getLogger("etl.jobs.fx")

UPSERT = """
INSERT INTO exchange_rates (rate_date, usd_brl_buy, usd_brl_sell, source, fetched_at)
VALUES (%s, %s, %s, 'BCB PTAX', now())
ON CONFLICT (rate_date) DO UPDATE SET usd_brl_buy = EXCLUDED.usd_brl_buy,
    usd_brl_sell = EXCLUDED.usd_brl_sell, fetched_at = now()
"""


def run(conn=None, http=None, days: int | None = None) -> dict:
    own = conn is None
    conn = conn or connect()
    http = http or HttpClient()
    days = days or int(os.getenv("ETL_FX_DAYS", "45"))
    try:
        end = config.today_br()
        quotes = ptax.fetch_period(http, end - timedelta(days=days), end)
        for q in quotes:
            conn.execute(UPSERT, (q.rate_date, q.cotacaoCompra, q.cotacaoVenda))
        conn.commit()
        log.info("fx: %d cotações gravadas", len(quotes))
        return {"quotes": len(quotes)}
    finally:
        if own:
            conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())

"""Recoleta em massa: procura TODOS os jogos do catálogo em TODAS as lojas conectadas (Steam, Epic, GOG, Nuuvem, Instant Gaming).

Zera as marcas de "já procurei e a loja não tinha" e roda a coleta de cada jogo sem a chamada de ofertas da CheapShark (que o ciclo normal
já faz); a CheapShark só é consultada para os jogos que ainda não têm id nela. Parar por limite de taxa é normal: rode de novo depois.
Uso: docker compose exec -T etl-runner python -m etl.jobs.backfill_stores
"""
import logging

from etl import config, fx
from etl.clients.cheapshark import CheapSharkClient
from etl.db import connect
from etl.http import HttpClient, RateLimited
from etl.jobs import ig_index, nuuvem_index
from etl.jobs.prices import GAME_COLS, refresh_game

log = logging.getLogger("etl.jobs.backfill_stores")


def run(conn=None, http=None, today=None) -> dict:
    own = conn is None
    conn = conn or connect()
    http = http or HttpClient()
    today = today or config.today_br()
    stats = {"games": 0, "snapshots": 0, "failed": 0}
    try:
        ig_index.run(conn=conn)
        nuuvem_index.run(conn=conn)
        found = fx.rate_from_db(conn, today)
        if not found:
            raise RuntimeError("sem cotação PTAX no banco; rode o ETL de câmbio antes")
        _, rate = found
        active = {r["store_id"] for r in conn.execute("SELECT store_id FROM stores WHERE is_active")}
        conn.execute("UPDATE games SET epic_checked_at = NULL WHERE epic_slug IS NULL")
        conn.execute("UPDATE games SET gog_checked_at = NULL WHERE gog_id IS NULL")
        conn.execute("UPDATE games SET nuuvem_checked_at = NULL WHERE nuuvem_slug IS NULL")
        conn.execute("UPDATE games SET ig_checked_at = NULL WHERE instant_gaming_url IS NULL")
        conn.execute("UPDATE games SET steam_checked_at = NULL, cs_checked_at = NULL")
        conn.commit()
        cs = CheapSharkClient(http)
        for g in conn.execute(f"SELECT {GAME_COLS} FROM games ORDER BY game_id").fetchall():
            stats["games"] += 1
            try:
                refresh_game(conn, http, cs, g, rate, active, today, stats, with_deals=False)
            except RateLimited as exc:
                log.error("%s; interrompendo (rode de novo depois)", exc)
                stats["rate_limited"] = True
                conn.rollback()
                break
            except Exception as exc:
                log.error("falha em %s: %s", g["title"], exc)
                stats["failed"] += 1
                conn.rollback()
        log.info("backfill: %s", stats)
        return stats
    finally:
        if own:
            conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())

"""Catálogo inicial: cadastra aos poucos os jogos mais populares da Steam (que ainda não estão no banco).

Roda dentro do `etl.jobs.all` com limite pequeno por execução (respeita o limite da Steam, ~200 req/5 min). Quem não rende
oferta (grátis, DLC, sem preço) vai para `popular_skip` e só é reavaliado depois de SKIP_DAYS.
"""
import argparse
import logging

from etl import discovery
from etl.clients import steam
from etl.clients.steam_popular import popular_app_ids
from etl.db import connect
from etl.discovery import Candidate
from etl.http import HttpClient

log = logging.getLogger("etl.jobs.popular")
LIMIT = 20       # jogos tentados por execução
SKIP_DAYS = 30   # quanto tempo lembrar de um descarte


def run(limit: int = LIMIT, conn=None, http: HttpClient | None = None) -> dict:
    own = conn is None
    conn = conn or connect()
    http = http or HttpClient(pause=0.5, retries=1)
    try:
        ids = popular_app_ids(http)
        _, known, _ = discovery._known(conn)
        skipped = {r["steam_app_id"] for r in conn.execute(
            "SELECT steam_app_id FROM popular_skip WHERE skipped_at > now() - make_interval(days => %s)", (SKIP_DAYS,))}
        todo = [i for i in ids if i not in known and i not in skipped][:limit]
        cands = []
        for app_id in todo:
            meta = steam.fetch_meta(http, app_id)
            if meta and meta.get("name") and meta.get("type") == "game":
                cands.append(Candidate(discovery.clean_title(meta["name"]), steam_id=app_id))
            else:
                conn.execute("INSERT INTO popular_skip (steam_app_id, reason) VALUES (%s, 'nao_e_jogo') ON CONFLICT (steam_app_id) DO UPDATE SET skipped_at = now()", (app_id,))
        conn.commit()
        created = discovery.register(conn, http, cands, max_new=len(cands)) if cands else []
        made = {r["steam_app_id"] for r in conn.execute("SELECT steam_app_id FROM games WHERE game_id = ANY(%s)", (created,))} if created else set()
        for c in cands:  # sem oferta de PC (grátis, tirado de venda…): não tenta de novo por um tempo
            if c.steam_id not in made:
                conn.execute("INSERT INTO popular_skip (steam_app_id, reason) VALUES (%s, 'sem_oferta') ON CONFLICT (steam_app_id) DO UPDATE SET skipped_at = now()", (c.steam_id,))
        conn.commit()
        log.info("populares: %d na lista, %d tentados, %d cadastrados", len(ids), len(todo), len(created))
        return {"listed": len(ids), "tried": len(todo), "created": len(created)}
    finally:
        if own:
            conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=LIMIT)
    print(run(ap.parse_args().limit))

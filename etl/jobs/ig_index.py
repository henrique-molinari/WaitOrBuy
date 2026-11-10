"""Job: índice do catálogo da Instant Gaming (sitemap oficial → tabela ig_catalog). No máximo 1x por dia."""
import logging

from etl.clients import instant_gaming
from etl.db import connect
from etl.http import HttpClient

log = logging.getLogger("etl.jobs.ig_index")
MAX_AGE_HOURS = 24


def run(conn=None, http=None, force: bool = False) -> dict:
    own = conn is None
    conn = conn or connect()
    try:
        fresh = conn.execute(
            "SELECT 1 FROM etl_meta WHERE key = 'ig_index' AND updated_at > now() - make_interval(hours => %s)",
            (MAX_AGE_HOURS,)).fetchone()
        if fresh and not force:
            return {"skipped": True}
        rows = instant_gaming.fetch_index(http or HttpClient(pause=0.5))
        if not rows:
            log.warning("sitemap da Instant Gaming sem produtos; índice anterior mantido")
            return {"rows": 0}
        with conn.transaction():
            conn.execute("DELETE FROM ig_catalog")
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO ig_catalog (ig_id, url, norm_title, platform) VALUES (%(ig_id)s, %(url)s, %(norm_title)s, %(platform)s) "
                    "ON CONFLICT (ig_id) DO NOTHING", rows)
            conn.execute("INSERT INTO etl_meta (key, value) VALUES ('ig_index', %s) "
                         "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()", (str(len(rows)),))
        conn.commit()
        log.info("ig_index: %d produtos de PC", len(rows))
        return {"rows": len(rows)}
    finally:
        if own:
            conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run(force=True))

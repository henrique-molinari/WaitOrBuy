"""Job: índice do catálogo da Nuuvem (sitemap oficial → tabela nuuvem_catalog). No máximo 1x por dia."""
import logging

from etl.clients import nuuvem
from etl.db import connect
from etl.http import HttpClient

log = logging.getLogger("etl.jobs.nuuvem_index")
MAX_AGE_HOURS = 24


def run(conn=None, http=None, force: bool = False) -> dict:
    own = conn is None
    conn = conn or connect()
    try:
        fresh = conn.execute(
            "SELECT 1 FROM etl_meta WHERE key = 'nuuvem_index' AND updated_at > now() - make_interval(hours => %s)",
            (MAX_AGE_HOURS,)).fetchone()
        if fresh and not force:
            return {"skipped": True}
        rows = nuuvem.fetch_index(http or HttpClient(pause=0.5, timeout=60.0))
        if not rows:
            log.warning("sitemap da Nuuvem sem produtos; índice anterior mantido")
            return {"rows": 0}
        with conn.transaction():
            conn.execute("DELETE FROM nuuvem_catalog")
            with conn.cursor() as cur:
                cur.executemany("INSERT INTO nuuvem_catalog (slug, norm_title) VALUES (%(slug)s, %(norm_title)s) ON CONFLICT (slug) DO NOTHING", rows)
            conn.execute("INSERT INTO etl_meta (key, value) VALUES ('nuuvem_index', %s) "
                         "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()", (str(len(rows)),))
        conn.commit()
        log.info("nuuvem_index: %d produtos", len(rows))
        return {"rows": len(rows)}
    finally:
        if own:
            conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run(force=True))

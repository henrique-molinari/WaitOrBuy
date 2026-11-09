"""Agendador local: roda `all` a cada ETL_INTERVAL_HOURS e aciona a avaliação de alertas no backend."""
import logging
import time
from pathlib import Path

import httpx

from etl import config, migrate
from etl.jobs import all as all_jobs

log = logging.getLogger("etl.runner")
ALIVE = Path("/tmp/etl_alive")


def evaluate_alerts() -> None:
    try:
        r = httpx.post(f"{config.BACKEND_URL}/api/admin/alerts/evaluate",
                       headers={"X-Admin-Token": config.ADMIN_TOKEN}, timeout=60)
        log.info("avaliação de alertas: %s %s", r.status_code, r.text[:200])
    except Exception as exc:
        log.error("avaliação de alertas falhou: %s", exc)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    ALIVE.touch()  # saudável desde o início; o agendador roda em seguida
    migrate.run()  # idempotente: garante esquema antes do primeiro ciclo
    first = True
    while True:
        # O primeiro ciclo só roda se o banco estiver vazio, para não repetir ETL em cada restart.
        try:
            if first and _has_data():
                log.info("dados já presentes; primeiro ciclo adiado até o próximo intervalo")
            else:
                all_jobs.run()
                evaluate_alerts()
        except Exception as exc:
            log.exception("ciclo ETL falhou: %s", exc)
        first = False
        deadline = time.time() + config.INTERVAL_HOURS * 3600
        while time.time() < deadline:
            ALIVE.touch()
            time.sleep(30)


def _has_data() -> bool:
    from etl.db import connect

    with connect() as conn:
        return conn.execute("SELECT 1 FROM price_snapshots LIMIT 1").fetchone() is not None


if __name__ == "__main__":
    main()

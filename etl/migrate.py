"""Aplica migrações SQL versionadas de db/migrations (idempotente)."""
import logging
from pathlib import Path

from etl.db import connect

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "db" / "migrations"
log = logging.getLogger("etl.migrate")


def run() -> list[str]:
    applied_now: list[str] = []
    with connect() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())")
        conn.commit()
        done = {r["version"] for r in conn.execute("SELECT version FROM schema_migrations")}
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in done:
                continue
            with conn.transaction():
                conn.execute(path.read_text(encoding="utf-8"))
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.name,))
            applied_now.append(path.name)
    return applied_now


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    applied = run()
    print(f"migrações aplicadas agora: {applied or 'nenhuma (já atualizado)'}")

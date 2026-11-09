"""CLI: python -m app.cli evaluate-alerts"""
import json
import logging
import sys

from app import db
from app.services import alerts


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO)
    if argv[:1] != ["evaluate-alerts"]:
        print("uso: python -m app.cli evaluate-alerts", file=sys.stderr)
        return 2
    with db.pool().connection() as conn:
        print(json.dumps(alerts.evaluate(conn)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

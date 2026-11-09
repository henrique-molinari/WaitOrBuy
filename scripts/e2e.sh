#!/usr/bin/env bash
cd "$(dirname "$0")/.."
docker compose exec -T backend python scripts/demo_user.py && docker compose exec -T backend python scripts/e2e_flow.py

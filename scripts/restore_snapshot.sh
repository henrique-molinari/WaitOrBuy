#!/usr/bin/env bash
# Plano B sem internet: restaura preços/jogos/câmbio do snapshot (db/demo_snapshot.sql) e regera o catálogo com fixtures.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose exec -T postgres psql -q -U waitorbuy -c "TRUNCATE price_snapshots, games, stores, exchange_rates RESTART IDENTITY CASCADE"
docker compose exec -T postgres psql -q -U waitorbuy < db/demo_snapshot.sql
docker compose exec -T postgres psql -q -U waitorbuy -c "INSERT INTO stores (store_id, name, domain, is_active) VALUES (100, 'Nuuvem', 'nuuvem.com', true), (101, 'Instant Gaming', 'instant-gaming.com', true) ON CONFLICT (store_id) DO NOTHING"
docker compose exec -T postgres psql -q -U waitorbuy -c "SELECT setval('games_game_id_seq', (SELECT max(game_id) FROM games)); SELECT setval('price_snapshots_snapshot_id_seq', (SELECT max(snapshot_id) FROM price_snapshots))"
docker compose exec -T etl-runner python -m etl.jobs.catalog
echo "snapshot restaurado: os preços \"reais\" têm a data da coleta original; rode o seed-demo para regerar o histórico simulado até hoje"

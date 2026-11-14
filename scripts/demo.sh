#!/usr/bin/env bash
# make demo: sobe tudo, migra, carrega dados (ETL real; se falhar, snapshot offline), seed, usuário demo.
set -uo pipefail
cd "$(dirname "$0")/.."
if [ ! -f .env ]; then cp .env.example .env; TOKEN=$(head -c 24 /dev/urandom | od -An -tx1 | tr -d " 
"); sed -i "s/^ADMIN_TOKEN=.*/ADMIN_TOKEN=$TOKEN/" .env; fi
docker compose up -d --build --wait || { echo "falha ao subir os serviços"; exit 1; }
docker compose exec -T etl-runner python -m etl.migrate
if ! docker compose exec -T etl-runner python -m etl.jobs.all; then
  echo ">> ETL real falhou; usando snapshot offline"; bash scripts/restore_snapshot.sh
fi
N=$(docker compose exec -T postgres psql -U waitorbuy -tAc "select count(*) from games g where exists (select 1 from price_snapshots p where p.game_id=g.game_id and not p.is_simulated and p.snapshot_date >= current_date - 1)" | tr -d '\r ')
if [ "${N:-0}" -lt 30 ]; then
  echo ">> menos de 30 jogos com preço de hoje ($N): usando o snapshot offline (substitui os preços coletados nesta execução)"; bash scripts/restore_snapshot.sh
fi
docker compose exec -T etl-runner python -m etl.jobs.seed_demo
docker compose exec -T backend python scripts/demo_user.py
cat <<MSG

== WaitOrBuy pronto ==
Frontend : http://localhost:5173
API/docs : http://localhost:8001/docs
Login demo (só no modo emulador): demo@waitorbuy.test / demo-123456
Alerta ponta a ponta: crie um alerta com alvo acima do preço atual e rode: make alerts-eval
MSG

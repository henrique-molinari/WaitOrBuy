#!/usr/bin/env bash
# Roda o pipeline Apache Hop da cotação PTAX (hop/pipelines/wf2_fx.hpl) contra o Postgres do compose.
# Uso: bash scripts/hop_fx.sh [dias]   (padrão: 45). Precisa da stack no ar (docker compose up -d --wait).
set -euo pipefail
cd "$(dirname "$0")/.."
export MSYS_NO_PATHCONV=1
DIAS="${1:-45}"
get() { grep -E "^$1=" .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r"' || true; }
DB_USER="$(get POSTGRES_USER)"; DB_PASS="$(get POSTGRES_PASSWORD)"; DB_NAME="$(get POSTGRES_DB)"
FIM="$(date +%m-%d-%Y)"; INI="$(date -d "$DIAS days ago" +%m-%d-%Y)"
REDE="$(docker inspect "$(docker compose ps -q postgres)" --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}')"
HOP_DIR="$(pwd -W 2>/dev/null || pwd)/hop"
docker run --rm --network "$REDE" -v "$HOP_DIR:/work/hop" \
  -v "$HOP_DIR/metadata:/opt/hop/config/projects/default/metadata" -e HOP_LOG_LEVEL=Basic \
  --entrypoint /opt/hop/hop-run.sh apache/hop:2.10.0 \
  -f /work/hop/pipelines/wf2_fx.hpl -r local \
  -p DATA_INI="$INI" -p DATA_FIM="$FIM" \
  -p DB_HOST=postgres -p DB_NAME="${DB_NAME:-waitorbuy}" -p DB_USER="${DB_USER:-waitorbuy}" -p DB_PASS="${DB_PASS:-waitorbuy}"

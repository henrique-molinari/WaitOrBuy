#!/usr/bin/env bash
# Fluxo ponta a ponta. Sobe o backend em modo emulador, roda o fluxo e devolve o backend ao modo normal (Firebase real).
cd "$(dirname "$0")/.."
source scripts/_emulator.sh
$DCE up -d --build --wait firebase backend || exit 1
$DCE exec -T backend python scripts/demo_user.py && $DCE exec -T backend python scripts/e2e_flow.py
RC=$?
restore_real_backend
exit $RC

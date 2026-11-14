#!/usr/bin/env bash
# Roda a suíte COMPLETA (inclui os testes que usam o Auth/Firestore Emulator) sem mexer no backend em execução.
cd "$(dirname "$0")/.."
source scripts/_emulator.sh
$DCE up -d --wait firebase || exit 1
$DCE run --build --rm -T backend pytest -q "$@"

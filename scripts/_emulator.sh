# Funções comuns dos scripts em modo emulador (use com: source scripts/_emulator.sh).
DCE="docker compose -f docker-compose.yml -f docker-compose.emulator.yml --profile emulator"
# Devolve o backend ao modo escolhido no .env (COMPOSE_FILE), que pode ser o Firebase real.
restore_default_backend() { docker compose up -d --wait backend >/dev/null 2>&1; }

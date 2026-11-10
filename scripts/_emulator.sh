# Funções comuns dos scripts em modo emulador (use com: source scripts/_emulator.sh).
DCE="docker compose -f docker-compose.yml -f docker-compose.emulator.yml --profile emulator"
restore_real_backend() { docker compose up -d --wait backend >/dev/null 2>&1; }

# Uso: make up && make migrate && make etl && make seed-demo
DC = docker compose

up:
	$(DC) up -d --build --wait

down:
	$(DC) down

reset:
	$(DC) down -v

migrate:
	$(DC) exec etl-runner python -m etl.migrate

etl:
	$(DC) exec etl-runner python -m etl.jobs.all

seed-demo:
	$(DC) exec etl-runner python -m etl.jobs.seed_demo

alerts-eval:
	$(DC) exec backend python -m app.cli evaluate-alerts

lint:
	$(DC) exec backend ruff check .

test:
	$(DC) exec backend pytest -q

verify: lint test

logs:
	$(DC) logs -f --tail=100

.PHONY: up down reset migrate etl seed-demo alerts-eval lint test verify logs

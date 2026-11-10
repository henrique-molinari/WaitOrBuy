# Checklist de requisitos (briefing R1–R8)

| # | Requisito | Evidência (arquivo / comando) | Status |
|---|---|---|---|
| R1 | 3+ tecnologias de armazenamento | PostgreSQL ([db/migrations/001_init.sql](../db/migrations/001_init.sql)), MongoDB ([etl/jobs/catalog.py](../etl/jobs/catalog.py)), Firestore ([firebase/firestore.rules](../firebase/firestore.rules), [backend/app/routers/me.py](../backend/app/routers/me.py)). `docker compose ps` → 3 bancos/emulador healthy; contagens verificadas (Postgres 178 preços reais + simulados; Mongo 36 documentos) | OK |
| R2 | 1+ ferramenta de integração (Hop ou KNIME) | Jobs Python equivalentes funcionando ([etl/jobs/](../etl/jobs/)). Guia KNIME em [knime/BUILD_GUIDE.md](../knime/BUILD_GUIDE.md); **workflows `.knwf` não montados** | PARCIAL (KNIME visual: passo manual ~1 h) |
| R3 | Consumo de 1+ API externa | CheapShark, Steam e PTAX consumidas de verdade: `docker compose exec etl-runner python -m etl.jobs.all` ([docs/API_NOTES.md](API_NOTES.md)). RAWG só com fixtures (sem chave) | OK (RAWG: NÃO VERIFICADO) |
| R4 | Backend em Python | FastAPI: [backend/app/main.py](../backend/app/main.py); `http://localhost:8001/docs`; `make verify` (66 testes) | OK |
| R5 | Frontend em React | [frontend/](../frontend/) React + TypeScript + Recharts — **protótipo mínimo**; versão final fica com outra pessoa. `docker compose up frontend` build OK (tsc + vite) | PARCIAL (protótipo) |
| R6 | Processo de integração/consolidação | Preços multi-loja + câmbio + catálogo + histórico numa visão única (`/api/games/{id}`); [etl/jobs/prices.py](../etl/jobs/prices.py); testes [tests/test_etl_integration.py](../tests/test_etl_integration.py) | OK |
| R7 | Interface para visualizar/usar resultados | Protótipo: busca, lista ordenada, jogo com gráfico e vale esperar, login, wishlist, alertas, notificações. Fluxo de dados validado por `make e2e` (API + emulador); **a interface em navegador não foi testada automaticamente** | PARCIAL |
| R8 | Demonstração funcional | `make demo` ([scripts/demo.sh](../scripts/demo.sh)); roteiro [DEMO_SCRIPT.md](DEMO_SCRIPT.md). Teste a frio: ver PROGRESS.md | PARCIAL: a frio terminou com a aplicação utilizável (frontend 200, e2e OK), mas o ETL real foi bloqueado pela CheapShark (429) e o script usou o snapshot offline; ver PROGRESS.md |

Não verificado: push FCM real, listener do Firestore em navegador real (regras e dados validados por REST), KNIME visual, `make` GNU neste Windows.

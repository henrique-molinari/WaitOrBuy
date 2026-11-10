# WaitOrBuy

Comparador de preços de jogos de PC: mostra o mesmo jogo em várias lojas, em reais, do mais barato ao mais caro; guarda histórico de preços; avisa quando o jogo chega ao preço desejado; e responde **"vale esperar?"** (preço atual × histórico × grandes liquidações). Projeto de Integração de Dados (PostgreSQL + MongoDB + Firebase, ETL em Python, API FastAPI).

> **Status do frontend:** `frontend/` tem a v1 da interface (busca, página do jogo com veredito e histórico, wishlist, alertas, avisos e login), construída sobre o contrato [docs/CONTRACTS.md](docs/CONTRACTS.md) e a identidade visual descrita em [frontend/DESIGN.md](frontend/DESIGN.md). Para ver as telas sem subir a stack: `cd frontend && npm install && npm run dev:mock` (dados fictícios; login `demo@waitorbuy.test` / `demo-123456`). Com a stack no ar (`make demo`), `npm run dev` usa a API real.

## Rodar a demonstração
Pré-requisitos: Docker Desktop (Compose v2), `make` (no Windows: `choco install make` ou use `bash scripts/demo.sh`), internet para o ETL real (sem internet, o script usa o snapshot offline).

```bash
git clone <repo> && cd waitorbuy
cp .env.example .env      # opcional: o demo.sh copia sozinho
make demo                 # = bash scripts/demo.sh: sobe tudo, migra, ETL, histórico simulado, usuário demo
# abrir http://localhost:5173  (login: demo@waitorbuy.test / demo-123456)
```
Offline: `make demo-offline` assume as imagens Docker já construídas/baixadas (o build precisa de rede uma vez) e recria o usuário demo. O ETL real leva alguns minutos (a CheapShark exige pausa entre chamadas). Passo a passo manual equivalente: `make up && make migrate && make etl && make seed-demo`.

| Alvo | O que faz |
|---|---|
| `make demo` / `make demo-offline` | sobe tudo / restaura o snapshot sem internet (`db/demo_snapshot.sql`) |
| `make verify` | `ruff` + `pytest` no backend em execução (os 4 testes que precisam do Auth Emulator são pulados em modo Firebase real) |
| `make test-emulator` | suíte **completa** (inclui os testes de Auth/Firestore) contra o Firebase Emulator, sem mexer no backend em execução |
| `make e2e` | fluxo ponta a ponta (usa o emulador: sobe o backend em modo emulador e depois o devolve ao modo normal) |
| `make alerts-eval` | avalia os alertas agora (o etl-runner também faz isso após cada coleta) |
| `make reset` | `docker compose down -v` (apaga os dados) |

**Dois modos de Firebase.** (1) *Firebase real* (padrão do `docker-compose.yml`: `FIREBASE_CREDENTIALS` aponta para `firebase/credentials.json`, que está no `.gitignore`; o frontend usa as chaves de `frontend/.env`). (2) *Emulador* (`docker-compose.emulator.yml` + `--profile emulator`: `FIREBASE_AUTH_EMULATOR_HOST`/`FIRESTORE_EMULATOR_HOST`, projeto `demo-waitorbuy`, usuário demo `demo@waitorbuy.test`), usado por `test-emulator` e `e2e`. A avaliação de alertas usa o índice `firebase/firestore.indexes.json`; se ele ainda não foi publicado no projeto real (`firebase deploy --only firestore:indexes`), o backend filtra em memória e registra um aviso.

URLs: frontend `:5173`, API/Swagger `:8001/docs`, Postgres `:5433` (só loopback), Mongo `:27018` (só loopback), Firestore Emulator `:8080`, Auth Emulator `:9099`.

## Variáveis (.env.example)
`DATABASE_URL`, `MONGO_URL`, `RAWG_API_KEY` (opcional), `ETL_INTERVAL_HOURS` (4), `ETL_PAUSE_SECONDS` (1.5), `ADMIN_TOKEN` (**troque** fora de dev), `AFFILIATE_TAG`, `FRONTEND_ORIGIN` (CORS), `FIREBASE_PROJECT_ID` (`demo-waitorbuy`), `FIRESTORE_EMULATOR_HOST`, `FIREBASE_AUTH_EMULATOR_HOST`, `FIREBASE_CREDENTIALS` (opcional, push FCM), `RATE_LIMIT_PER_MIN` (300 por IP).

## Honestidade dos dados
- **Preço real em R$**: Steam (`steam_brl`), GOG (`gog_brl`), Epic (`epic_brl`), Nuuvem (`nuuvem_brl`) e Instant Gaming (`instantgaming_brl`), lidos das páginas/APIs públicas. GOG e Epic usam endpoints públicos **não oficiais**; se falharem, o jogo continua com a estimativa da CheapShark. **Demais lojas**: USD da CheapShark × cotação de venda PTAX do Banco Central (`converted_usd`) — **estimativa**, pode divergir do preço real em R$.
- **Histórico**: só acumula com o tempo; `make seed-demo` gera 180 dias **simulados** (`is_simulated=true`, determinísticos). O dado real nunca é sobrescrito pelo simulado.
- **Catálogo**: sem `RAWG_API_KEY`, gêneros e tempo de jogo vêm de fixtures (`is_fixture=true`, estimativas editoriais).
- Datas de liquidações sazonais são aproximadas ("verificar calendário oficial").

## Lojas conectadas
**Busca de qualquer jogo de PC:** a busca descobre, ao vivo, jogos que ainda não estão no banco (Steam, Epic, GOG e CheapShark ao mesmo tempo), cadastra e já coleta os preços; só entram jogos-base de PC (sem DLC, trilha ou jogo só de console). Detalhes e todos os endpoints em [docs/API.md](docs/API.md).

Steam, Nuuvem, Instant Gaming (preço real em R$) + GOG, Epic Games Store, Humble Store, Fanatical, GreenManGaming, Gamesplanet, GamersGate, GameBillet, IndieGala, WinGameStore (e Ubisoft/DreamGame quando têm oferta) via CheapShark. Dados auxiliares: Banco Central (PTAX), Steam appdetails e RAWG (opcional). A lista viva está em `GET /api/platforms` e na tela **Lojas**. Detalhes e fontes descartadas: `docs/API_NOTES.md`.

## Passos manuais
1. **KNIME**: montar os 3 workflows na GUI seguindo [knime/BUILD_GUIDE.md](knime/BUILD_GUIDE.md) (~1 h). Os jobs Python equivalentes já fazem tudo.
2. Chave gratuita da RAWG no `.env` para trocar fixtures por dados reais.
3. Credenciais Firebase reais só se quiserem push FCM (não verificado).
4. Revisão jurídica: [docs/REVISAR_JURIDICO.md](docs/REVISAR_JURIDICO.md).

## Estrutura
`etl/` jobs e clientes · `backend/app/` API · `db/migrations/` SQL versionado · `firebase/` emuladores e regras · `frontend/` protótipo · `knime/` guia · `scripts/` demo/e2e · `tests/` pytest · `docs/` contrato, arquitetura, dicionário, roteiro.
Documentos: [API](docs/API.md) · [ARCHITECTURE](docs/ARCHITECTURE.md) · [DATA_DICTIONARY](docs/DATA_DICTIONARY.md) · [APRESENTACAO](docs/APRESENTACAO.md) · [DEMO_SCRIPT](docs/DEMO_SCRIPT.md) · [CHECKLIST_REQUISITOS](docs/CHECKLIST_REQUISITOS.md) · [API_NOTES](docs/API_NOTES.md).

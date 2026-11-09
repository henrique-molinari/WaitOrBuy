# KNIME — guia de montagem (3 workflows)

> **PASSO MANUAL (~1 h):** os `.knwf` não são editados à mão; monte-os na GUI do KNIME Analytics Platform (5.x) seguindo este guia e exporte para `knime/workflows/`. O sistema já roda de ponta a ponta com os jobs Python equivalentes (`python -m etl.jobs.<job>`), que os workflows reproduzem ou chamam.

Pré-requisitos: KNIME 5.x; extensões *KNIME Database*, *KNIME JSON-Processing*, *KNIME Python Integration*; PostgreSQL em `localhost:5433` (usuário/senha/DB do `.env`) e MongoDB em `localhost:27018` (subir com `docker compose up -d postgres mongo`). Variáveis de fluxo (Flow Variables) comuns: `db_url`, `ua = "WaitOrBuy-Academic/0.1 (student project)"`.

Atalho de menor esforço (válido para os 3): nó **Python Script (Labs)** executando `subprocess.run(["python","-m","etl.jobs.<job>"], cwd=<raiz do repo>)`; o workflow fica “Table Creator → Python Script → DB Reader (validação)”. A cadeia detalhada abaixo é a versão visual completa.

## Workflow 1 — Preços (`wf1_prices`)
**Objetivo:** preço do dia por jogo e loja (CheapShark em USD→BRL + Steam em BRL real) em `price_snapshots`.
**Agendamento:** KNIME Server/Hub schedule a cada 4 h, ou `knime -nosplash -application org.knime.product.KNIME_BATCH_APPLICATION -workflowFile=wf1_prices.knwf`.
**Cadeia de nós:**
1. *DB Reader* `SELECT game_id, cheapshark_game_id, steam_app_id FROM games WHERE tracked AND cheapshark_game_id IS NOT NULL`
2. *String Manipulation* → URL `https://www.cheapshark.com/api/1.0/games?id=` + `cheapshark_game_id`
3. *GET Request* (cabeçalho `User-Agent` = `ua`; atraso 1 s entre chamadas; retries 3)
4. *JSON Path* (`$.deals[*]` → storeID, dealID, price, retailPrice, savings) → *Ungroup*
5. *Row Filter* excluir `storeID = 1` (Steam entra pelo ramo BRL) e lojas inativas (*Reference Row Filter* contra `stores`)
6. *DB Reader* `SELECT usd_brl_sell FROM exchange_rates ORDER BY rate_date DESC LIMIT 1` → *Cross Joiner*
7. *Math Formula* `price_brl = round(price * usd_brl_sell, 2)`; `price_origin = "converted_usd"`
8. Ramo Steam: *GET Request* `https://store.steampowered.com/api/appdetails?appids=<app>&cc=br&filters=price_overview` → *JSON Path* `price_overview.final`/`initial`/`discount_percent` → *Math Formula* `/100`; `price_origin = "steam_brl"`
9. *Concatenate* dos dois ramos → *DB Writer* (upsert) em `price_snapshots` com `ON CONFLICT (game_id, store_id, snapshot_date)` (use *DB SQL Executor* com a mesma instrução de `etl/jobs/prices.py`).
**Parâmetros:** `ua`, pausa, `db_url`. **Validar:** `SELECT price_origin, count(*) FROM price_snapshots WHERE snapshot_date = current_date GROUP BY 1;` (rodar 2× não aumenta a contagem).

## Workflow 2 — Câmbio PTAX (`wf2_fx`)
**Objetivo:** cotação oficial do dólar (venda/compra) em `exchange_rates`.
**Agendamento:** diário, após 13h30 (boletim de fechamento do BC).
**Cadeia:** *Table Creator/Date&Time Creation* (hoje e hoje−45) → *String Manipulation* (datas `MM-dd-yyyy`) → *GET Request* `https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@di,dataFinalCotacao=@df)?@di='<ini>'&@df='<fim>'&$format=json` → *JSON Path* `$.value[*]` (cotacaoCompra, cotacaoVenda, dataHoraCotacao) → *Row Filter* (descartar nulos) → *String to Date* (`rate_date` = 10 primeiros caracteres) → *DB SQL Executor* upsert `ON CONFLICT (rate_date)`.
**Validar:** `SELECT * FROM exchange_rates ORDER BY rate_date DESC LIMIT 3;` — fins de semana não têm linha (a conversão usa a última cotação anterior).

## Workflow 3 — Catálogo RAWG → MongoDB (`wf3_catalog`)
**Objetivo:** documento de cada jogo (capa, gêneros, nota, tempo médio de jogo) na coleção `games` do MongoDB.
**Agendamento:** diário (os metadados mudam pouco).
**Cadeia:** *DB Reader* (`games` rastreados) → *GET Request* `https://api.rawg.io/api/games?search=<título>&search_precise=true&page_size=1&key=<RAWG_API_KEY>` → *JSON Path* `results[0].id` → *GET Request* `/api/games/<id>?key=...` → *JSON Path* (background_image, genres[*].name, platforms[*].platform.name, rating, metacritic, released, playtime, description_raw) → *Math Formula/Rule Engine* (playtime 0 → usar estimativa e marcar `playtime_source="fixture"`) → *Column Expressions* para montar o documento → *MongoDB Writer* (operação *Upsert* por `game_id`; índice único `game_id`).
**Parâmetros:** `RAWG_API_KEY` (sem chave use o nó Python `python -m etl.jobs.catalog`, que grava fixtures rotuladas `is_fixture=true`). **Validar:** `db.games.countDocuments({})` ≥ 30 e `db.games.findOne({slug:"hades"})`.

## Registro de execução
Preencher ao montar: data, versão do KNIME, saída da validação de cada workflow.

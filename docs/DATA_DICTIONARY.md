# Dicionário de dados

DDL: [db/migrations/001_init.sql](../db/migrations/001_init.sql). Contratos de API: [CONTRACTS.md](CONTRACTS.md).

## PostgreSQL
**stores** — `store_id` (smallint PK, id da CheapShark), `name`, `domain` (nulo), `is_active`.
**games** — `game_id` (serial PK), `title`, `slug` (único), `cheapshark_game_id` (único, nulo), `steam_app_id` (nulo), `rawg_id` (nulo), `tracked`, `created_at`.
**price_snapshots** — um preço por jogo/loja/dia (`UNIQUE(game_id, store_id, snapshot_date)`):
`price_brl` preço em reais · `price_original` + `currency_original` (USD ou BRL) · `fx_rate` (PTAX de venda usada; nulo na Steam) · `normal_price_brl` preço cheio · `discount_pct` · `deal_url` · `price_origin` (`steam_brl` real | `converted_usd` estimado) · `is_simulated` (histórico de demonstração) · `captured_at`.
**exchange_rates** — `rate_date` (PK, só dias úteis), `usd_brl_buy`, `usd_brl_sell`, `source`, `fetched_at`.
**seasonal_sales** — janelas recorrentes (`start_month/day`–`end_month/day`, podem virar o ano); `rule` = `black_friday` | `cyber_monday` para datas calculadas (4ª sexta de novembro e a segunda seguinte); `source_note` = "verificar calendário oficial".
**schema_migrations** — controle das migrações.
**Views** — `v_latest_price` (último preço real por jogo/loja), `v_daily_best` (menor preço do dia por jogo), `v_price_stats` (mínimo, média geral, média 90 dias, nº de dias com ponto, primeiro dia).

## MongoDB (`waitorbuy.games`, índice único `game_id`)
`game_id, slug, title, rawg_id, background_image, genres[], platforms[], rating, metacritic, released, playtime_hours, playtime_source ("rawg"|"fixture"), description, fetched_at, is_fixture`.

## Firestore
`users/{uid}/wishlist/{gameId}` `{game_id, added_at}` ·
`users/{uid}/alerts/{alertId}` `{game_id, target_price_brl, store_id|null, active, last_triggered_price|null, last_triggered_at|null, created_at}` ·
`users/{uid}/notifications/{id}` `{title, body, game_id, price_brl, store_id, created_at, read}` ·
`users/{uid}/devices/{token}` `{token, platform, created_at}`.
Regras: [firebase/firestore.rules](../firebase/firestore.rules) — cada usuário só acessa `users/{seu uid}/**`.

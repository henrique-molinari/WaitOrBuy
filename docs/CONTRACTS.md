# CONTRACTS — WaitOrBuy (ETL ↔ backend ↔ frontend)

Fonte única de formatos. Mudou algo: atualize aqui, o modelo pydantic (`backend/app/schemas.py`) e os testes no mesmo passo.
Convenções: valores em BRL com 2 casas; `price_origin` em toda oferta; `is_simulated` / `is_fixture` sempre expostos; `null` só onde indicado.

## 1. PostgreSQL
DDL oficial: [db/migrations/001_init.sql](../db/migrations/001_init.sql) (aplicada por `make migrate`, controle em `schema_migrations`).

| Objeto | Resumo |
|---|---|
| `stores(store_id smallint PK, name, domain null, is_active)` | id = `storeID` da CheapShark |
| `games(game_id serial PK, title, slug UNIQUE, cheapshark_game_id UNIQUE null, steam_app_id null, rawg_id null, tracked, created_at)` | |
| `price_snapshots(game_id, store_id, snapshot_date, captured_at, price_brl, price_original, currency_original, fx_rate null, normal_price_brl null, discount_pct, deal_url null, price_origin, is_simulated)` | `UNIQUE(game_id, store_id, snapshot_date)`; upsert mantém o último valor do dia; dado real sobrescreve simulado, nunca o contrário |
| `exchange_rates(rate_date PK, usd_brl_buy, usd_brl_sell, source, fetched_at)` | conversão usa `usd_brl_sell` da última `rate_date <= data` |
| `seasonal_sales(id, name, scope, rule null, start_month.., end_day, typical_discount_note, source_note)` | Black Friday / Cyber Monday por `rule` (calculadas) |
| `v_latest_price` | último preço **real** (não simulado) por jogo e loja |
| `v_daily_best` | menor preço do dia por jogo (todas as lojas, inclui simulado) |
| `v_price_stats` | `min_price_brl, avg_price_brl, avg_90d_brl, points, first_day` por jogo |

`price_origin`: `steam_brl` (preço real em BRL da Steam, cc=br) | `converted_usd` (USD CheapShark × PTAX venda; **estimativa**). A linha Steam da CheapShark é descartada.

## 2. MongoDB — db `waitorbuy`, coleção `games`
Índice único: `game_id`.
```json
{
  "game_id": 1, "slug": "hades", "title": "Hades", "rawg_id": null,
  "background_image": "https://cdn.cloudflare.steamstatic.com/steam/apps/1145360/header.jpg",
  "genres": ["Roguelike", "Ação"], "platforms": ["PC"], "rating": null, "metacritic": null,
  "released": null, "playtime_hours": 22, "playtime_source": "fixture",
  "description": null, "fetched_at": "2026-11-09T18:00:00Z", "is_fixture": true
}
```
`playtime_hours` número ou `null`. Fixtures (sem `RAWG_API_KEY`) têm `is_fixture=true`; valores de tempo de jogo de fixture vêm de `etl/tracked_games.yml` (estimativa editorial, não medição).

## 3. Firestore (projeto `demo-waitorbuy` em dev)
```
users/{uid}/wishlist/{gameId}       {game_id:int, added_at:timestamp}
users/{uid}/alerts/{alertId}        {game_id:int, target_price_brl:number, store_id:int|null, active:bool,
                                     last_triggered_price:number|null, last_triggered_at:timestamp|null, created_at:timestamp}
users/{uid}/notifications/{id}      {title, body, game_id:int, price_brl:number, store_id:int, created_at:timestamp, read:bool}
users/{uid}/devices/{token}         {token, platform:string|null, created_at:timestamp}
```
Regras (`firebase/firestore.rules`): cada usuário só lê/escreve `users/{uid}/**` com `request.auth.uid == uid`; todo o resto negado. O backend (Admin SDK) ignora as regras e valida o token ele mesmo. Avaliação de alertas usa `collection_group("alerts")`.

## 4. API (FastAPI) — base `http://localhost:8001`, docs em `/docs`
Erros: `{"error": {"code": "<codigo>", "message": "<texto pt-BR>"}}` — códigos: `validation_error` (422), `not_found` (404), `unauthorized` (401), `forbidden` (403), `conflict` (409), `internal_error` (500).
Auth: `Authorization: Bearer <ID token do Firebase Auth>`; admin: header `X-Admin-Token: <ADMIN_TOKEN>`.
Links de oferta recebem `aff=<AFFILIATE_TAG>` quando a variável está definida.

**Offer** (objeto comum)
```json
{"store_id": 25, "store_name": "Epic Games Store", "price_brl": 68.93, "normal_price_brl": 137.86,
 "discount_pct": 50.0, "price_origin": "converted_usd", "is_estimated": true,
 "deal_url": "https://www.cheapshark.com/redirect?dealID=...", "captured_at": "2026-11-09T18:00:00Z"}
```
`price_origin` ∈ `steam_brl | converted_usd | nuuvem_brl | instantgaming_brl | epic_brl | gog_brl`; `is_estimated = (price_origin == "converted_usd")`. `normal_price_brl` pode ser `null`.

### GET /health → 200
`{"status":"ok","postgres":true,"mongo":true,"firestore":true}` (503 com `status:"degraded"` se algum cair).

### GET /api/search
Parâmetros (todos opcionais): `q` (0–100 chars; vazio = navega o catálogo), `limit` 1–60 (24), `store` (repetível: `?store=1&store=101`), `max_price` (>0, BRL), `min_discount` 0–100, `sort` = `relevance|price|discount|title|stores` (422 `invalid_sort`), `live` (true: consulta as lojas ao vivo quando o termo não foi pesquisado nas últimas 6 h).
Retorna jogos acompanhados cujo título contém todas as palavras de `q`; `offers` já filtradas e ordenadas do menor preço ao maior. `facets` conta ofertas por loja **antes** dos filtros (alimenta o filtro de lojas); `discovered` = jogos novos cadastrados nesta busca; `live_error` = aviso quando uma fonte externa não respondeu. **Busca tolerante:** se nenhum título contém o termo, a API procura títulos parecidos (erro de digitação, letras trocadas; `pg_trgm`, similaridade ≥ 0,35) e devolve `fuzzy: true` e `did_you_mean` (título mais parecido). Sem acerto, `fuzzy: false` e `did_you_mean: null`. O frontend deve avisar que são resultados parecidos.
```json
{"query":"hades","count":1,"discovered":0,"live_error":null,"fuzzy":false,"did_you_mean":null,
 "facets":[{"store_id":1,"name":"Steam","count":2}],
 "results":[{"game_id":1,"slug":"hades","title":"Hades","thumb":"https://.../header.jpg",
  "best_offer":{"...Offer..."},"offers":[{"...Offer, ordenadas por price_brl asc..."}],
  "is_fixture":true,"genres":["Roguelike"],"discovered":false}]}
```

### GET /api/recommended
Parâmetros: `exclude` (repetível, ids dos jogos já listados, até 60), `limit` 1–24 (8). Sugestões para a tela de resultados: jogos do mesmo gênero dos `exclude` primeiro, depois os de maior desconto; cada item traz o menor preço vigente.
```json
{"count":1,"items":[{"game_id":2,"slug":"celeste","title":"Celeste","thumb":null,"offer":{"...Offer..."},"reason":"genero"}]}
```
`reason` ∈ `genero | promocao`.

### GET /api/suggest?q=ha
Autocompletar: banco local primeiro; com menos de 5 acertos (e 3+ letras) completa com jogos da Steam ao vivo (`live`, padrão true; cache de 1 h por texto; falha da Steam é silenciosa). Até 8.
```json
{"query":"had","suggestions":[{"game_id":1,"slug":"hades","title":"Hades","live":false},{"game_id":null,"slug":null,"title":"Hades II","live":true}]}
```
`live: true` = jogo ainda fora do banco (`game_id`/`slug` nulos): o frontend manda para `#/busca?q=<título>`, o que o cadastra e precifica.

### GET /api/platforms
Lojas conectadas com ofertas reais e provedores de dados.
```json
{"count":13,"total_games":38,
 "platforms":[{"store_id":101,"name":"Instant Gaming","domain":"instant-gaming.com","price_kind":"brl_real",
   "source":"Instant Gaming (sitemap + página do produto)","games":26,"last_captured_at":"2026-11-10T..."}],
 "providers":[{"name":"CheapShark","role":"...","needs_key":false,"enabled":true}]}
```
`price_kind` (calculado das ofertas vigentes de cada loja): `brl_real` (todas em R$ real: Steam, Nuuvem, Instant Gaming, e GOG/Epic quando a loja respondeu), `mixed` (parte real, parte ainda estimada) ou `usd_converted` (só estimativa CheapShark × PTAX).

### GET /api/games/{game_id}
404 `not_found` se o jogo não existe.
```json
{"game_id":1,"slug":"hades","title":"Hades",
 "meta":{"background_image":"...","genres":["Roguelike"],"platforms":["PC"],"rating":null,"metacritic":null,
         "released":null,"description":null,"playtime_hours":22,"is_fixture":true},
 "offers":[{"...Offer..."}],"best_offer":{"...Offer..."},
 "stats":{"min_price_brl":24.9,"avg_price_brl":58.1,"avg_90d_brl":60.2,"points":181,"first_day":"2026-05-13","history_days":181,"has_simulated_history":true},
 "verdict":{"verdict":"COMPRAR_AGORA","confidence":"alta","based_on_simulated":true,"reasons":["R$ 24,90 está no menor preço histórico ou muito perto (mínimo R$ 24,90)."],
            "metrics":{"price_now":24.9,"min_ever":24.9,"avg_all":58.1,"avg_90d":60.2,"discount_pct":66.0,"days_to_next_sale":18,"sale_name":"Black Friday","history_days":181}},
 "next_sale":{"name":"Black Friday","start_date":"2026-11-27","days":18,"note":"verificar calendário oficial"},
 "playtime_hours":22,"price_per_hour":1.13}
```
`verdict.based_on_simulated` é `true` quando o histórico usado inclui dias simulados (a API acrescenta um motivo avisando). `verdict.verdict ∈ {COMPRAR_AGORA, ESPERAR, NEUTRO, INSUFICIENTE}`; `confidence ∈ {baixa, media, alta}`; `price_per_hour` e `playtime_hours` `null` se não houver tempo de jogo (> 0) ou preço; `best_offer` `null` se não há ofertas; `next_sale` pode ser `null`.

### GET /api/games/{game_id}/history?store=25&days=180
`store` opcional (id); sem `store` → melhor preço diário entre lojas. `days` 1–730 (padrão 180).
```json
{"game_id":1,"store_id":null,"days":180,"has_simulated":true,
 "points":[{"date":"2026-05-13","price_brl":59.9,"store_id":25,"is_simulated":true}]}
```
Em `points[].store_id` aparece a loja do menor preço do dia (ou a loja filtrada).

### GET /api/deals/home?limit=12
Maiores descontos atuais (1 oferta por jogo).
```json
{"count":1,"deals":[{"game_id":1,"slug":"hades","title":"Hades","thumb":"...","offer":{"...Offer..."}}]}
```

### GET /api/fx
`{"rate_date":"2026-11-06","usd_brl_buy":5.5007,"usd_brl_sell":5.5013,"source":"BCB PTAX","fetched_at":"..."}` — 404 se sem cotação.

### Autenticados (Bearer)
Sem token/ inválido → 401 `unauthorized`.

- `GET /api/me/wishlist` → `{"items":[{"game_id":1,"slug":"hades","title":"Hades","thumb":"...","added_at":"...","best_offer":{...}|null}]}`
- `POST /api/me/wishlist` body `{"game_id":1}` → 201 `{"game_id":1,"added":true}` (404 se jogo inexistente; idempotente).
- `DELETE /api/me/wishlist/{game_id}` → 200 `{"game_id":1,"removed":true}`.
- `GET /api/me/wishlist/cart`
```json
{"game_count":2,"stores":[
  {"store_id":25,"store_name":"Epic Games Store","total_brl":150.5,"complete":true,"missing_games":[],"game_count":2,
   "items":[{"game_id":1,"title":"Hades","price_brl":68.93,"price_origin":"converted_usd","deal_url":"..."}]},
  {"store_id":1,"store_name":"Steam","total_brl":73.99,"complete":false,"missing_games":[{"game_id":2,"title":"Celeste"}],"game_count":1,"items":[...]}],
 "best_mix":{"total_brl":120.0,"items":[{"game_id":1,"title":"Hades","store_id":25,"store_name":"Epic Games Store","price_brl":68.93,"price_origin":"converted_usd","deal_url":"..."}],
             "missing_games":[],"savings_vs_best_store_brl":30.5}}
```
Lojas completas primeiro (menor total), depois incompletas (menor total). `best_mix.savings_vs_best_store_brl` é `null` se nenhuma loja é completa. Wishlist vazia → `stores: []`, `best_mix.total_brl: 0`.
- `GET /api/me/alerts` → `{"items":[{"alert_id":"abc","game_id":1,"title":"Hades","target_price_brl":30.0,"store_id":null,"active":true,"last_triggered_price":null,"last_triggered_at":null}]}`
- **Pedido do front (Home personalizada), opcional, o front funciona sem:** `GET /api/me/wishlist` → cada item com `verdict` (`COMPRAR_AGORA|ESPERAR|NEUTRO|INSUFICIENTE|null`, o mesmo de `/api/games/{id}`); `GET /api/me/alerts` → cada item com `current_price_brl` (menor oferta atual, `null` se sem oferta). Sem esses campos o front busca `/api/games/{id}` por alerta (até 4) e não mostra veredito na wishlist.
- `POST /api/me/alerts` body `{"game_id":1,"target_price_brl":30.0,"store_id":null}` → 201 alerta criado (`target_price_brl` > 0; 404 jogo inexistente).
- `DELETE /api/me/alerts/{alert_id}` → `{"alert_id":"abc","removed":true}` (404 se não existe).
- `GET /api/me/notifications?limit=50` → `{"unread":1,"items":[{"id":"n1","title":"Hades chegou ao seu preço","body":"Hades por R$ 29,90 na Steam (alvo R$ 30,00).","game_id":1,"price_brl":29.9,"store_id":1,"created_at":"...","read":false}]}` (mais recentes primeiro).
- `POST /api/me/notifications/{id}/read` → `{"id":"n1","read":true}` (404 se não existe).
- `POST /api/me/devices` body `{"token":"<FCM>","platform":"web"}` → 201 `{"registered":true}`.
- **Pedidos do front (push web), o front já está pronto:** (1) `send_push` deve mandar também `data={"game_id":"<id>"}` (o service worker `frontend/public/push-sw.js` abre `/#/jogo/<id>` ao clicar; sem `data` abre `/#/avisos`); (2) `DELETE /api/me/devices/{token}` para o usuário desligar no app (hoje só dá para desligar nas permissões do navegador); (3) remover o token do dispositivo quando o FCM devolver `UNREGISTERED`. Front precisa das variáveis `VITE_FIREBASE_*` e `VITE_FCM_VAPID_KEY` (ver `frontend/.env.example`).

### Interno
- `POST /api/admin/alerts/evaluate[?uid=<uid>]` (uid opcional restringe a um usuário; usado nos testes) header `X-Admin-Token` (403 `forbidden` se errado) → `{"alerts_checked":3,"triggered":1,"rearmed":0,"notifications_created":1,"push":"nao_configurado"}`; `push ∈ {"nao_configurado","enviado"}`.
- CLI equivalente: `python -m app.cli evaluate-alerts`.

## 5. Regra "vale esperar?"
Ver [backend/app/services/verdict.py](../backend/app/services/verdict.py); limiares em `backend/app/config.py`. Ordem: INSUFICIENTE (< 5 dias de histórico ou sem mínimo) → A (≤ 1,05× mínimo: COMPRAR_AGORA) → B (liquidação grande ≤ 30 dias e > 1,15× mínimo: ESPERAR) → C (≥ 0,95× média 90d, desconto < 20%, sem liquidação ≤ 30 dias: ESPERAR) → D NEUTRO.

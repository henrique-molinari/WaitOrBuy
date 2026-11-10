# API do WaitOrBuy

Referência da API REST (FastAPI). Documentação interativa gerada pelo próprio servidor: `http://localhost:8001/docs` (Swagger) e `/openapi.json`.
Os formatos aqui seguem [CONTRACTS.md](CONTRACTS.md) (contrato entre ETL, backend e frontend) e foram conferidos contra a API em execução.

- **Base:** `http://localhost:8001` (dentro do Docker, `http://backend:8000`)
- **Formato:** JSON, UTF-8. Datas em ISO 8601 com fuso `America/Sao_Paulo`. Valores em reais (`price_brl`, número com 2 casas).
- **CORS:** só `FRONTEND_ORIGIN` (padrão `http://localhost:5173`), métodos `GET`, `POST`, `DELETE`.
- **Limite de uso:** 300 requisições por minuto por IP (`RATE_LIMIT_PER_MIN`); acima disso, `429`.

## 1. Autenticação

| Grupo | Como autenticar |
|---|---|
| Público (busca, jogos, ofertas, câmbio, lojas, `/health`) | nenhuma |
| `/api/me/*` (wishlist, alertas, notificações, dispositivos) | `Authorization: Bearer <ID token do Firebase Auth>` |
| `/api/admin/*` | `X-Admin-Token: <ADMIN_TOKEN do .env>` |

O token do usuário é o *ID token* do Firebase Auth (o frontend o obtém no login). Token ausente, inválido ou expirado → `401`.

## 2. Erros

Todo erro tem o mesmo corpo, com `message` em português pronta para mostrar ao usuário e `code` estável para o frontend:

```json
{"error": {"code": "not_found", "message": "Não encontramos o que você procurou."}}
```

| HTTP | `code` | Quando |
|---|---|---|
| 401 | `unauthorized` | token ausente, inválido ou expirado |
| 403 | `forbidden` | `X-Admin-Token` errado |
| 404 | `not_found` | jogo, loja, alerta ou notificação inexistente (ou rota inexistente) |
| 405 | `method_not_allowed` | método HTTP não permitido na rota |
| 409 | `conflict` | reservado para conflito de estado (hoje nenhuma rota o usa) |
| 422 | `validation_error` / `invalid_sort` | parâmetro inválido, ex.: `Entrada inválida em 'path.game_id': precisa ser um número inteiro.` |
| 429 | `rate_limited` | limite de requisições (cabeçalho `Retry-After`) |
| 503 | `servico_indisponivel` | Firestore, PostgreSQL ou MongoDB fora do ar (cabeçalho `Retry-After: 30`) |
| 500 | `internal_error` | erro inesperado; a mensagem é genérica e **nunca** expõe detalhes internos |

## 3. Honestidade dos preços

Todo preço traz a **origem** (`price_origin`) e o booleano `is_estimated`:

| `price_origin` | Significado | `is_estimated` |
|---|---|---|
| `steam_brl` | Steam, API pública, R$ real | `false` |
| `epic_brl` | Epic Games Store, GraphQL público da loja, R$ real | `false` |
| `gog_brl` | GOG, catálogo/preços públicos, R$ real | `false` |
| `nuuvem_brl` | Nuuvem, página do produto, R$ real | `false` |
| `instantgaming_brl` | Instant Gaming, página do produto, R$ real | `false` |
| `converted_usd` | outras lojas: USD da CheapShark × cotação PTAX do Banco Central | **`true`** (estimativa, pode divergir do preço real) |

O histórico de preços pode ter dias **simulados** (`is_simulated: true`) para a demonstração; a interface deve sempre sinalizar isso.

## 4. Busca e descoberta

### `GET /api/search`

Busca jogos de PC e compara o preço entre as lojas, do mais barato ao mais caro.

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `q` | string (até 100) | `""` | termos da busca; sem acento e sem diferenciar maiúsculas (`pokemon` acha `Pokémon`). Vazio navega o catálogo |
| `limit` | inteiro 1–60 | 24 | máximo de jogos na resposta |
| `store` | inteiro, repetível | — | só ofertas destas lojas (`?store=1&store=25`) |
| `max_price` | número > 0 | — | preço máximo (R$) |
| `min_discount` | número 0–100 | 0 | desconto mínimo (%) |
| `sort` | `relevance`, `price`, `discount`, `title`, `stores` | `relevance` | ordenação; outro valor → `422 invalid_sort` |
| `live` | booleano | `true` | procura jogos novos nas lojas quando o banco ainda não os conhece |

**Descoberta ao vivo (`live=true`).** Qualquer jogo de PC vendido nas lojas conectadas aparece, mesmo que ainda não esteja no banco. Ao receber uma busca com 3 ou mais caracteres, a API consulta ao mesmo tempo Steam, Epic, GOG e CheapShark, junta os títulos (a mesma obra em várias lojas vira um jogo só), cadastra até 8 jogos novos e já coleta os preços em todas as lojas. Regras:

- só entra **jogo-base de PC**: DLC, trilhas sonoras, passes de temporada e jogos grátis ou sem preço (por exemplo, retirados de venda) ficam de fora;
- é preciso provar que é PC: ter oferta na Steam, Epic, GOG ou Instant Gaming (Humble e Nuuvem sozinhas não bastam, pois vendem chaves de Nintendo Switch);
- jogos exclusivos de console (Pokémon, Zelda, FIFA) não aparecem por isso;
- a mesma busca só dispara a descoberta de novo depois de 6 horas;
- a primeira busca por um termo novo leva de alguns segundos a cerca de 15 s; as seguintes são imediatas;
- se uma loja não responde, a busca continua com as outras. Se todas falham, vem `live_error` e o que já está no banco.

**Resposta `200`:**

```json
{
  "query": "mortal kombat",
  "count": 3,
  "discovered": 3,
  "live_error": null,
  "results": [
    {
      "game_id": 161, "slug": "mortal-kombat-1", "title": "Mortal Kombat 1",
      "thumb": "https://…/header.jpg", "genres": ["Ação"], "is_fixture": false, "discovered": true,
      "best_offer": {"store_id": 15, "store_name": "Fanatical", "price_brl": 38.55, "normal_price_brl": 385.97,
                     "discount_pct": 90.0, "price_origin": "converted_usd", "is_estimated": true,
                     "deal_url": "https://www.cheapshark.com/redirect?dealID=…", "captured_at": "2026-11-10T10:41:03-03:00"},
      "offers": ["… todas as ofertas, ordenadas por preço, no mesmo formato de best_offer"]
    }
  ],
  "facets": [{"store_id": 1, "name": "Steam", "count": 3}]
}
```

`facets` lista as lojas com ofertas nos jogos achados (para montar filtros), contando antes dos filtros `store`, `max_price` e `min_discount`. `discovered` é quantos jogos novos esta busca cadastrou.

### `GET /api/suggest?q=<texto>`

Autocompletar rápido, **só no banco local** (não consulta lojas). `q` é obrigatório (1–100 caracteres). Até 8 sugestões, sem acento.

```json
{"query": "hol", "suggestions": [{"game_id": 79, "slug": "hollow", "title": "Hollow"}]}
```

### `GET /api/platforms`

Lojas conectadas (as que têm ofertas vigentes) e provedores de dados.

```json
{
  "count": 13, "total_games": 188,
  "platforms": [{"store_id": 1, "name": "Steam", "domain": "steampowered.com", "price_kind": "brl_real",
                 "source": "Steam (API oficial)", "games": 43, "last_captured_at": "2026-11-10T10:41:03-03:00"}],
  "providers": [{"name": "GOG", "role": "Preço real em BRL (catálogo e preços públicos)", "needs_key": false, "enabled": true}]
}
```

`price_kind` é calculado das ofertas vigentes de cada loja: `brl_real` (todas em R$ real), `mixed` (parte real, parte estimada) ou `usd_converted` (só estimativa).

## 5. Jogos e ofertas

### `GET /api/games/{game_id}`

Página do jogo: metadados, ofertas, estatísticas, veredito "vale esperar?" e próxima liquidação. `404` se não existir.

```json
{
  "game_id": 2, "slug": "hades-ii", "title": "Hades II",
  "meta": {"background_image": "https://…", "genres": ["Roguelike", "Ação"], "platforms": ["PC"], "rating": null,
           "metacritic": null, "released": null, "description": null, "playtime_hours": 25.0, "is_fixture": true},
  "offers": ["lista de Offer, do mais barato ao mais caro"],
  "best_offer": {"store_id": 1, "store_name": "Steam", "price_brl": 88.99, "…": "…"},
  "stats": {"min_price_brl": 38.03, "avg_price_brl": 80.56, "avg_90d_brl": 88.15, "points": 182,
            "first_day": "2026-05-13", "history_days": 182, "has_simulated_history": true},
  "verdict": {"verdict": "ESPERAR", "confidence": "alta",
              "reasons": ["Steam Autumn Sale começa em 15 dia(s) …", "R$ 88,99 é 134% acima do menor preço, R$ 38,03."],
              "metrics": {"price_now": 88.99, "min_ever": 38.03, "days_to_next_sale": 15, "sale_name": "Steam Autumn Sale"},
              "based_on_simulated": true},
  "next_sale": {"name": "Steam Autumn Sale", "start_date": "2026-11-25", "days": 15, "note": "datas aproximadas"},
  "playtime_hours": 25.0
}
```

`verdict.verdict` ∈ `COMPRAR_AGORA`, `ESPERAR`, `NEUTRO` ou `INSUFICIENTE` (histórico curto demais); `confidence` ∈ `baixa`, `média`, `alta`. A regra completa está na skill `vale-esperar` e em `backend/app/services/verdict.py`. `based_on_simulated` indica que o veredito usou histórico simulado.

### `GET /api/games/{game_id}/history`

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `store` | inteiro > 0 | todas | histórico de uma loja |
| `days` | inteiro 1–730 | 180 | janela em dias |

```json
{"game_id": 2, "store_id": null, "days": 3, "has_simulated": true,
 "points": [{"date": "2026-11-07", "price_brl": 90.72, "store_id": 1, "is_simulated": true}]}
```

Sem `store`, cada ponto é o **melhor preço do dia** entre as lojas.

### `GET /api/deals/home?limit=12`

Maiores descontos para a página inicial (`limit` 1–50). Um item por jogo.

```json
{"count": 1, "deals": [{"game_id": 79, "slug": "hollow", "title": "Hollow", "thumb": "https://…", "offer": {"store_id": 21, "price_brl": 6.07, "discount_pct": 94.5, "…": "…"}}]}
```

### `GET /api/fx`

Cotação usada na conversão USD → BRL (venda PTAX do Banco Central).

```json
{"rate_date": "2026-11-09", "usd_brl_buy": 5.514, "usd_brl_sell": 5.5146, "source": "BCB PTAX", "fetched_at": "2026-11-10T04:47:18-03:00"}
```

### Objeto `Offer`

| Campo | Descrição |
|---|---|
| `store_id`, `store_name` | loja |
| `price_brl` | preço atual em R$ |
| `normal_price_brl` | preço sem desconto (pode ser `null`) |
| `discount_pct` | desconto em % |
| `price_origin`, `is_estimated` | ver [seção 3](#3-honestidade-dos-preços) |
| `deal_url` | link da oferta (pode levar a um link de afiliado se `AFFILIATE_TAG` estiver configurada) |
| `captured_at` | quando o preço foi coletado |

## 6. Área do usuário (exige `Authorization: Bearer`)

### Wishlist

| Método e rota | Corpo | Resposta |
|---|---|---|
| `GET /api/me/wishlist` | — | `{"items": [{"game_id", "slug", "title", "thumb", "added_at", "best_offer"}]}`, mais recentes primeiro |
| `POST /api/me/wishlist` | `{"game_id": 2}` | `201 {"game_id": 2, "added": true}` (idempotente); `404` se o jogo não existe |
| `DELETE /api/me/wishlist/{game_id}` | — | `{"game_id": 2, "removed": true}` |
| `GET /api/me/wishlist/cart` | — | carrinho (abaixo) |

**Carrinho** (`/api/me/wishlist/cart`): quanto custa a wishlist inteira em cada loja e a melhor combinação entre lojas.

```json
{
  "game_count": 3,
  "stores": [{"store_id": 1, "store_name": "Steam", "total_brl": 281.98, "complete": true, "game_count": 3, "missing_games": [],
              "items": [{"game_id": 2, "title": "Hades II", "price_brl": 88.99, "price_origin": "steam_brl", "deal_url": "https://…"}]}],
  "best_mix": {"total_brl": 250.10, "savings_vs_best_store_brl": 31.88, "missing_games": [],
               "items": [{"game_id": 2, "title": "Hades II", "price_brl": 80.0, "store_id": 25, "store_name": "Epic Games Store", "…": "…"}]}
}
```

Lojas completas (com todos os jogos) vêm primeiro, depois por total.

### Alertas de preço

| Método e rota | Corpo | Resposta |
|---|---|---|
| `GET /api/me/alerts` | — | `{"items": [AlertOut]}` |
| `POST /api/me/alerts` | `{"game_id": 2, "target_price_brl": 70.0, "store_id": null}` | `201 AlertOut`; `store_id` opcional (vazio = qualquer loja); `404` se jogo ou loja não existe |
| `DELETE /api/me/alerts/{alert_id}` | — | `{"alert_id": "…", "removed": true}`; `404` se não existe |

`AlertOut`: `{"alert_id", "game_id", "title", "target_price_brl", "store_id", "active", "last_triggered_price", "last_triggered_at"}`.

Funcionamento: o alerta dispara quando o menor preço (ou o da loja escolhida) fica **igual ou abaixo do alvo**, não repete enquanto o preço seguir abaixo, dispara de novo se cair mais e **rearma** quando o preço volta a ficar acima do alvo.

### Notificações e dispositivos

| Método e rota | Corpo | Resposta |
|---|---|---|
| `GET /api/me/notifications?limit=50` | — | `{"unread": 1, "items": [{"id", "title", "body", "game_id", "price_brl", "store_id", "created_at", "read"}]}` (`limit` 1–200, mais recentes primeiro) |
| `POST /api/me/notifications/{id}/read` | — | `{"id": "…", "read": true}`; `404` se não existe |
| `POST /api/me/devices` | `{"token": "<token FCM, 10 a 4096 caracteres>", "platform": "web"}` | `201 {"registered": true}` |

O frontend também escuta as notificações direto no Firestore (`users/{uid}/notifications`); as regras do Firestore só permitem ler os dados do próprio usuário e a escrita é feita só pelo backend.

## 7. Infraestrutura e administração

### `GET /health`

```json
{"status": "ok", "postgres": true, "mongo": true, "firestore": true}
```

`200` se os três respondem; senão `503` com `"status": "degraded"` e o que falhou.

### `POST /api/admin/alerts/evaluate[?uid=<uid>]`

Avalia todos os alertas ativos agora (ou só os de `uid`). Exige `X-Admin-Token`. O `etl-runner` chama este endpoint após cada coleta.

```json
{"alerts_checked": 1, "triggered": 1, "rearmed": 0, "notifications_created": 1, "push": "nao_configurado"}
```

`push` é `enviado` quando há credenciais FCM e ao menos um push saiu, senão `nao_configurado`. Se o índice `alerts.active` do Firestore (`firebase/firestore.indexes.json`) ainda não foi publicado no projeto, a avaliação filtra em memória e continua funcionando.

## 8. Exemplos

```bash
# buscar (descobre o jogo se ainda não existir)
curl "http://localhost:8001/api/search?q=resident%20evil&sort=price&limit=10"

# só ofertas em R$ real da Steam e da Epic, até R$ 100
curl "http://localhost:8001/api/search?q=witcher&store=1&store=25&max_price=100"

# página do jogo e histórico de 90 dias
curl "http://localhost:8001/api/games/2"
curl "http://localhost:8001/api/games/2/history?days=90"

# criar alerta (token do Firebase)
curl -X POST "http://localhost:8001/api/me/alerts" \
  -H "Authorization: Bearer $ID_TOKEN" -H "Content-Type: application/json" \
  -d '{"game_id": 2, "target_price_brl": 70}'

# avaliar alertas (admin)
curl -X POST "http://localhost:8001/api/admin/alerts/evaluate" -H "X-Admin-Token: $ADMIN_TOKEN"
```

Uma coleção pronta para o Insomnia está em [`insomnia/`](../insomnia/README.md).

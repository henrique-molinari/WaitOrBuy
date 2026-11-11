# Notas das APIs externas (verificadas com chamadas reais em 2026-11-09)

## CheapShark (https://www.cheapshark.com/api/1.0) — sem chave
- **Exige User-Agent descritivo**: sem ele responde `{"error": "Missing or generic User-Agent header..."}`. Usamos `WaitOrBuy-Academic/0.1 (student project)`.
- `GET /stores` → lista de `{storeID:"1", storeName, isActive:0|1, images}`. IDs são strings. 35 lojas; ativas incluem Steam(1), GamersGate(2), GreenManGaming(3), GOG(7), Humble(11), Uplay(13), Fanatical(15), WinGameStore(21), GameBillet(23), Epic(25), Gamesplanet(27), IndieGala(30), DreamGame(35).
- `GET /games?title=hades&limit=N` → `[{gameID, steamAppID|null, cheapest, cheapestDealID, external, internalName, thumb}]`. Valores numéricos vêm como string.
- `GET /games?id=196149` → `{info:{title, steamAppID, thumb}, cheapestPriceEver:{price, date(epoch)}, deals:[{storeID, dealID, price, retailPrice, savings}]}`. Preços em USD (string). Só traz lojas com oferta.
- `GET /deals?storeID=1&pageSize=N` → ofertas com `salePrice`, `normalPrice`, `savings`, `steamAppID`, etc.
- Link da oferta: `https://www.cheapshark.com/redirect?dealID=<dealID>` (dealID já vem URL-encoded).
- Limite não documentado em números; usamos pausa de 0,3 s entre chamadas e retry com backoff em 429/5xx.

## Steam Store (appdetails)
- `GET https://store.steampowered.com/api/appdetails?appids=1145360&cc=br&filters=price_overview`
- Resposta: `{"1145360":{"success":true,"data":{"price_overview":{"currency":"BRL","initial":7399,"final":7399,"discount_percent":0,...}}}}`. Valores em **centavos**.
- Jogo grátis/sem preço: `data` é `[]` ou sem `price_overview` → sem linha Steam. Limite informal ≈ 200 req/5 min: pausa de 0,5 s.
- Observação: o preço Steam BRL (R$ 73,99) difere muito da conversão do USD (US$ 24,99 × 5,50 = R$ 137): por isso a Steam usa `steam_brl`.

## Banco Central — PTAX (Olinda)
- Dia: `.../PTAX/versao/v1/odata/CotacaoDolarDia(dataCotacao=@dataCotacao)?@dataCotacao='11-06-2026'&$format=json` (MM-DD-AAAA).
- Período: `.../CotacaoDolarPeriodo(dataInicial=@di,dataFinalCotacao=@df)?@di='10-25-2026'&@df='11-08-2026'&$format=json`.
- `value:[{cotacaoCompra, cotacaoVenda, dataHoraCotacao:"2026-11-06 13:06:13.966"}]` — só dias úteis (sábado/domingo/feriado sem registro → usamos a última cotação disponível). Exemplo: 06/11/2026 venda 5,5013.

## RAWG (https://api.rawg.io/api) — chave gratuita
- `GET /games?search=<t>&search_precise=true&page_size=1&key=KEY` e `GET /games/{id}?key=KEY` (`description_raw`, `playtime`, `background_image`, `genres`, `platforms`, `rating`, `metacritic`, `released`).
- **NÃO VERIFICADO**: sem `RAWG_API_KEY` neste ambiente; o catálogo usa fixtures rotuladas `is_fixture=true`. Formato acima segue a documentação oficial.


## Nuuvem (https://www.nuuvem.com/br-pt/item/<slug>) — sem API pública, sem chave
- A Nuuvem só oferece Store API mediante aprovação da equipe; por isso lemos o **microdata schema.org** da página do produto (`priceCurrency=BRL`, `price`), permitida pelo robots.txt. A busca interna (`/search/`) é proibida e **não é usada**.
- O slug vem do **sitemap oficial** (`/sitemap.xml`, declarado no robots.txt; ~50 MB, só as URLs `/br-pt/item/`), indexado 1x por dia em `nuuvem_catalog` (`etl/jobs/nuuvem_index.py`). O jogo casa por título (igual ou edição, nunca sequência/DLC); se o índice não achar, o ETL ainda tenta `slugify(título)` (e sem "the-"). Sem página ou sem oferta = a loja não vende o jogo (nova tentativa após 7 dias). `nuuvem:` no `tracked_games.yml` sobrescreve. Recoleta em massa: `python -m etl.jobs.backfill_stores`.
- Verificado em 2026-11-10: `elden-ring` → R$ 247,05; `dark-souls-iii` → R$ 229,90. Algumas páginas (ex.: `cyberpunk-2077`) não trazem o microdata de preço → sem oferta (não inventamos preço).

## Instant Gaming (https://www.instant-gaming.com/pt/) — sem API pública, sem chave
- Não existe API aberta (há programa de afiliados com feed, sob aprovação). Lemos somente o que o robots.txt permite: **sitemap oficial** `sitemap_ig_products_pt[_2,_3].xml` (declarado no robots) e a **página do produto**. A busca (`/pt/pesquisar/`, `?q=`) é proibida e **não é usada**.
- Job `ig_index` (1x/dia): sitemap → tabela `ig_catalog` (id, URL, título normalizado), só PC e sem trava regional (`-europe`, `-estados-unidos`...). ~15,6 mil produtos em 2026-11-10.
- Preço: `itemprop=price` em BRL na página do produto; só vale se `BR` estiver em `eligibleRegion`. O casamento com o jogo é por **título normalizado exato** (sem chutes).
- `/pt/<id>-comprar-x/` redireciona para a URL canônica, mas o id não é descobrível sem o sitemap.

## Fontes avaliadas e NÃO usadas
- **IsThereAnyDeal**: `GET /service/shops/v1` (sem chave) lista 35 lojas e inclui Nuuvem, mas **não** a Instant Gaming; os preços exigem chave e aprovação. Fica como extensão futura.
- **gg.deals** (preços por Steam App ID, inclui keyshops): exige chave e atribuição; sem chave neste ambiente → não verificado.
- **Humble (API de busca)**: bloqueada por Cloudflare para clientes automatizados. Já é coberta via CheapShark.
- **Kinguin/G2A e similares**: marketplaces de chaves de terceiros, não considerados confiáveis.

## Descoberta ao vivo (busca)
`GET /api/search?q=` consulta o banco; se o termo não foi pesquisado nas últimas 6 h, `etl.discovery` busca na CheapShark, cadastra até 3 jogos novos, coleta preços (CheapShark + Steam + Nuuvem + Instant Gaming) e metadados (Steam appdetails, ou RAWG com chave). Jogo sem nenhuma oferta é descartado.


## Epic Games Store (https://store.epicgames.com/graphql) — sem chave, NÃO OFICIAL
- Não existe API pública documentada: usamos o GraphQL que o próprio site consulta. Verificado em 2026-11-10: `POST` com `searchStore(keywords, country:"BR", locale:"pt-BR", category:"games/edition/base|bundles/games|editors")` devolve `price(country).totalPrice {discountPrice, originalPrice, currencyCode:"BRL", currencyInfo{decimals}}` (centavos; Hades = 7399).
- A variável `$c` precisa ser `String!`. O jogo é escolhido por casamento de título (`etl/matching.py`: igual, ou o mesmo jogo em edição "Remastered/GOTY"; nunca sequência ou DLC) e só entre `BASE_GAME`/`BUNDLE`/`EDITION`. O link usa `offerMappings[pageType=productHome].pageSlug`.
- Pode mudar ou bloquear sem aviso: qualquer falha vira "sem preço" e o jogo segue com a estimativa da CheapShark. Jogo que a Epic não vende só é consultado de novo após 7 dias. Ver `docs/REVISAR_JURIDICO.md`.

## GOG — sem chave, NÃO OFICIAL
- Busca: `GET https://catalog.gog.com/v1/catalog?query=<título>&productType=in:game,pack&countryCode=BR&currencyCode=BRL&locale=en-US` (o prefixo `like:` não funciona com `query`). Preço: `GET https://api.gog.com/products/<id>/prices?countryCode=BR&currency=BRL` → `"finalPrice":"1435 BRL"` em **centavos**. Verificado em 2026-11-10 (The Witcher 3 Remastered = 159,99).
- Mesma regra de casamento de título da Epic. Fontes de terceiros citam 200 req/h por IP em `api.gog.com/products/*` (não verificado); o ETL consulta o preço de 1 jogo por chamada, com pausa.

## Steam — jogos populares (catálogo inicial), sem chave
- `GET https://api.steampowered.com/ISteamChartsService/GetMostPlayedGames/v1/` (oficial, top 100 por jogadores simultâneos), `GET https://store.steampowered.com/api/featuredcategories?cc=br` (mais vendidos, promoções, lançamentos) e SteamSpy `GET https://steamspy.com/api.php?request=top100in2weeks|top100forever` (terceiros). Só ids; nome, tipo e preço vêm do `appdetails` (BRL real). Verificado em 2026-11-10.
- `etl.jobs.popular` tenta 20 jogos por ciclo (pausa de 0,5 s). Descartes (grátis, DLC, sem preço) ficam em `popular_skip` por 30 dias.
- Autocompletar ao vivo: `GET store.steampowered.com/api/storesearch/?term=…&cc=br` devolve no máximo 10 itens (`count` é ignorado), muitos deles DLC; o cliente filtra.

## Fontes avaliadas e NÃO integradas (2026-11-10)
- **Humble Bundle**: sem API pública; `store/api/search` bloqueado por Cloudflare. **Fanatical**: sem API/feed público; só HTML. Ambos seguem via CheapShark (USD convertido, rotulado como estimativa).
- **Exigem cadastro/aprovação (sem chave não integra)**: Green Man Gaming (afiliados via Impact), Kinguin (API só para lojistas; afiliados via Awin), G2A (Export API com OAuth2), Eneba (API só para vendedores; feed de afiliados), Lomadee (token + Source ID; 10 req/min segundo guia de terceiros), Amazon (PA-API 5 descontinuada; Creators API exige vendas qualificadas). Fora do escopo desta entrega.

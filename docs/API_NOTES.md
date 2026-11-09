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

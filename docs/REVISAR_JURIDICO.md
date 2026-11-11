# Pontos para revisão jurídica

> Não é parecer jurídico. **Verificar termos atuais; revisar com advogado** antes de qualquer uso público ou comercial.

| Item | Observação |
|---|---|
| CheapShark API | Uso gratuito, exige User-Agent identificável e limita taxa (houve bloqueio temporário por IP em testes). Conferir termos e atribuição em apidocs.cheapshark.com. |
| Steam Store (appdetails) | Endpoint não documentado oficialmente para uso comercial; conferir os termos da Steam Web API / Store antes de publicar. |
| RAWG | Chave gratuita com exigências de atribuição e restrições de uso comercial; ler os termos (rawg.io/apidocs). Nenhuma chave está no repositório. |
| Banco Central (PTAX / Olinda) | Dados públicos abertos; citar a fonte. |
| Links de afiliado | `AFFILIATE_TAG` é opcional e não há programa real configurado. Cada loja tem programa e regras próprios (divulgação de afiliação, proibições de comparação, etc.). |
| Nuuvem / Instant Gaming | Sem API pública: lemos só páginas de produto e o sitemap oficial, respeitando o robots.txt (busca interna não é usada), com User-Agent identificável e pausa entre requisições. Conferir os termos de uso de cada loja; para uso comercial, pedir acesso à Store API da Nuuvem e ao feed de afiliados da Instant Gaming. |
| SteamSpy | API pública de terceiros usada só para listar ids de jogos populares (top100in2weeks/forever). Conferir termos e atribuição em steamspy.com/api.php; o job funciona sem ela (outras fontes de populares seguem). |
| Marcas das lojas | Nomes (Steam, Epic, GOG…) aparecem só como texto; nenhum logotipo foi usado. Conferir diretrizes de marca antes de usar logos. |
| Preços exibidos | Parte é estimativa (conversão do dólar) e parte do histórico é simulada; a interface precisa manter os avisos. |
| Dados pessoais | Firebase Auth/Firestore guardam e-mail e preferências: avaliar LGPD (base legal, política de privacidade, exclusão de conta). |
| Epic / GOG (endpoints não oficiais) | Lemos o GraphQL público da Epic (`store.epicgames.com/graphql`) e o catálogo/preços públicos da GOG (`catalog.gog.com`, `api.gog.com`), os mesmos que os sites usam, sem chave, com User-Agent identificável e pausa. Não há API oficial documentada: conferir termos de uso, e para uso comercial pedir parceria/afiliação. Podem mudar ou bloquear sem aviso. |
| Fontes que dependem de aprovação | Green Man Gaming (Impact), Kinguin/G2A (Awin / API de parceiros), Eneba, Lomadee e Amazon Creators API só entram com contrato de afiliado/parceiro. Humble e Fanatical não têm API pública e não são raspadas. |

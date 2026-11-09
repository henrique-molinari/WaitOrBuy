# Pontos para revisão jurídica

> Não é parecer jurídico. **Verificar termos atuais; revisar com advogado** antes de qualquer uso público ou comercial.

| Item | Observação |
|---|---|
| CheapShark API | Uso gratuito, exige User-Agent identificável e limita taxa (houve bloqueio temporário por IP em testes). Conferir termos e atribuição em apidocs.cheapshark.com. |
| Steam Store (appdetails) | Endpoint não documentado oficialmente para uso comercial; conferir os termos da Steam Web API / Store antes de publicar. |
| RAWG | Chave gratuita com exigências de atribuição e restrições de uso comercial; ler os termos (rawg.io/apidocs). Nenhuma chave está no repositório. |
| Banco Central (PTAX / Olinda) | Dados públicos abertos; citar a fonte. |
| Links de afiliado | `AFFILIATE_TAG` é opcional e não há programa real configurado. Cada loja tem programa e regras próprios (divulgação de afiliação, proibições de comparação, etc.). |
| Marcas das lojas | Nomes (Steam, Epic, GOG…) aparecem só como texto; nenhum logotipo foi usado. Conferir diretrizes de marca antes de usar logos. |
| Preços exibidos | Parte é estimativa (conversão do dólar) e parte do histórico é simulada; a interface precisa manter os avisos. |
| Dados pessoais | Firebase Auth/Firestore guardam e-mail e preferências: avaliar LGPD (base legal, política de privacidade, exclusão de conta). |

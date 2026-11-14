# Como o workflow do KNIME foi feito

Registro da construção do workflow `wf4_wishlist_email`: o que foi decidido, o que mudou no backend, os nós montados e os problemas que apareceram. Uso e configuração: [COMO_E_USADO.md](COMO_E_USADO.md).

## 1. Ponto de partida
O KNIME existia só como guia ([BUILD_GUIDE.md](BUILD_GUIDE.md), workflows 1 a 3), repetindo o que os jobs Python em `etl/jobs/` já fazem. Nenhum `.knwf` tinha sido montado, e nada no sistema o chamava. Decidiu-se dar a ele uma tarefa que **não existia** em outro lugar: o e-mail agrupado da wishlist.

## 2. Decisões de projeto

| Decisão | Motivo |
|---|---|
| "Bom preço" = veredito `COMPRAR_AGORA` do "vale esperar?" | É a mesma regra da tela do jogo; evita o e-mail dizer "compre" enquanto o site diz "espere". |
| O backend monta o e-mail inteiro; o KNIME só busca, envia e confirma | A regra fica em um lugar só e é testável. O KNIME fica simples. |
| Um e-mail por pessoa, com todos os jogos | Pedido do projeto: sem uma enxurrada de e-mails por jogo. |
| O aviso só é registrado **depois** do envio (endpoint separado) | Se o envio falhar, a pessoa não perde o aviso. |
| Não repete: só reavisa se o preço cair ou após 30 dias | Rodar duas vezes no mesmo dia não duplica e-mail. |
| O link do e-mail leva à página do jogo na plataforma | Pedido do projeto; usa `PUBLIC_URL` (ou o primeiro `FRONTEND_ORIGIN`). |
| Preço estimado e histórico simulado sempre sinalizados | Regra do projeto: nunca apresentar estimativa como preço real. |
| Roda sob demanda, fora do Docker | O KNIME é um programa de desktop; ficar 24/7 exigiria KNIME Server/Hub (pago). |

## 3. O que foi feito no backend

Código novo, com testes ([tests/test_wishlist_digest.py](../tests/test_wishlist_digest.py)):

- [backend/app/services/wishlist_digest.py](../backend/app/services/wishlist_digest.py): lê as wishlists (Firestore, `collection_group("wishlist")`), pega a melhor oferta e o veredito de cada jogo, agrupa por pessoa, descarta o que já foi avisado, busca o e-mail da conta no Firebase Auth e renderiza assunto, texto e HTML.
- `GET /api/admin/wishlist-deals[?uid=&cooldown_days=30]` em [backend/app/main.py](../backend/app/main.py): só lê. Devolve um e-mail pronto por pessoa e o `confirm_body`.
- `POST /api/admin/wishlist-deals/sent`: registra o aviso em `users/{uid}/wishlist_emails`.
- Ambos protegidos por `X-Admin-Token` (o mesmo `ADMIN_TOKEN` do `evaluate`).
- `firebase.user_email(uid)`, `settings.public_url`, os schemas `SentItem` e `WishlistEmailSent`.
- Documentado em [docs/API.md](../docs/API.md) e [docs/CONTRACTS.md](../docs/CONTRACTS.md).

O backend devolve o campo `confirm_body`, que é o JSON pronto do `POST /sent`. Isso foi acrescentado depois, porque montar esse JSON dentro do KNIME exigia converter uma coluna JSON em texto, o que se mostrou frágil.

## 4. O workflow, nó a nó

```
Credentials Configuration ─(variável)→ GET Request → JSON Path → JSON Path → Ungroup → Column Filter
   → Table Row to Variable Loop Start → Send Email → POST Request → Variable Loop End
```

| # | Nó | Configuração |
|---|---|---|
| 1 | *Credentials Configuration* | Guarda a senha de app do SMTP (variável `smtp`). Com "Save password" desmarcado, o KNIME pergunta a senha ao abrir. |
| 2 | *GET Request* | URL `http://localhost:8001/api/admin/wishlist-deals`; cabeçalho `X-Admin-Token`; autenticação *None*. A coluna `body` já sai como JSON. |
| 3 | *JSON Path* (entrada `body`) | `$.users[*]` → coluna `user` (JSON). |
| 4 | *JSON Path* (entrada `user`) | Seis consultas: `$.uid`, `$.email`, `$.subject`, `$.body_html`, `$.confirm_body` (String) e `$.items` (Json). |
| 5 | *Ungroup* | Nas seis colunas, com *Remove collection column* (e, recomendado, *Skip empty collections* e *Skip missing values*). |
| 6 | *Column Filter* | Mantém `uid`, `email`, `subject`, `body_html`, `confirm_body`. |
| 7 | *Table Row to Variable Loop Start* | Uma volta por pessoa; cada coluna vira variável de fluxo. |
| 8 | *Send Email* | SMTP configurado; aba *Flow Variables*: `to` = `email`, `subject` = `subject`; aba *Mail*: HTML, mensagem `$${Sbody_html}$$`. |
| 9 | *POST Request* | `http://localhost:8001/api/admin/wishlist-deals/sent`; cabeçalhos `X-Admin-Token` e `Content-Type: application/json`; corpo *Custom* ligado à variável `confirm_body`; erros HTTP em *Fail node*. Ligado ao *Send Email* por variável de fluxo, para só rodar depois do envio. |
| 10 | *Variable Loop End* | Fecha o laço. |

## 5. Problemas encontrados e como foram resolvidos

| Problema | Causa | Solução |
|---|---|---|
| Credencial não podia ser usada no cabeçalho do GET | A senha de uma credencial do KNIME só serve em campos de autenticação, não como texto | O token é digitado direto no cabeçalho; o nó de credenciais ficou para a senha SMTP. |
| "Authentication managed by Credential Input Port" | O GET Request tinha uma porta de credencial, que bloqueia outros tipos de autenticação | Remover a porta e deixar a autenticação em *None*. |
| `403 forbidden` no GET | Token digitado errado no cabeçalho | Conferir o valor igual ao `.env`; testar antes com `curl`. |
| `No column compatible to JSONValue` no JSON Path | O corpo da resposta tinha vindo como binário (por causa do erro 403) | Com o GET funcionando (200), o corpo já sai como JSON; os nós de conversão (*Binary Objects to Strings*, *String to JSON*) não foram necessários. |
| Colunas saíam como "Collection (List)" | O JSON Path novo devolvia listas de um item | Nó *Ungroup* nas colunas. |
| Montar o JSON da confirmação no KNIME | Exigiria converter JSON em texto dentro do *String Manipulation* | O backend passou a devolver `confirm_body` pronto. |
| `Must issue a STARTTLS command first` / timeout | SMTP em `NONE` e timeout de 2 s | `STARTTLS` na porta 587 e timeout de 20 s. |
| `Invalid Addresses ... <missing>` | O GET trouxe lista vazia (jogo já avisado), e o laço rodou com valores ausentes | Testar com `?cooldown_days=0`; marcar *Skip empty collections* e *Skip missing values* no *Ungroup*. |
| E-mail "não chegou" | O MailHog só guarda os e-mails na caixa local | Trocar para o SMTP do Gmail com senha de app. |

## 6. Como foi verificado

| O quê | Resultado |
|---|---|
| `GET /api/admin/wishlist-deals` com dado real | Devolveu 1 pessoa com o e-mail pronto (jogo, preço R$ 1,75 na GOG, aviso de histórico simulado). |
| Workflow executado no KNIME até o *POST Request* | `Status 200` e `{"uid": "...", "registered": 1}`. |
| Envio do e-mail | Funcionou nos testes manuais (primeiro MailHog, depois SMTP do Gmail). |
| `ruff` e `pytest` no container do backend | `ruff` limpo; 3 testes novos passam, 2 testes de fluxo completo **ficam pulados sem o emulador do Firebase**. |

## 7. O que **não** foi verificado (pendências)

- Os 2 testes de fluxo completo (precisam do emulador: `bash scripts/test_emulator.sh`; o Docker não conseguiu baixar a imagem no momento do teste).
- O **Variable Loop End** não tinha ficado verde na última execução relatada; é preciso conferir a ligação com o *POST Request* (porta de variável) e executar.
- Mais de uma pessoa ao mesmo tempo: o primeiro *JSON Path* (`$.users[*]`) saiu como um único JSON e pode devolver só a primeira pessoa. Testar com duas contas.
- O arquivo `.knwf` ainda não foi exportado para `knime/workflows/`.
- Link do e-mail com `localhost`: só abre onde a stack roda.
- Abertura do link no navegador e comportamento sem login não foram testados.
- Gmail com conta de faculdade pode bloquear senhas de app (administrador do domínio).

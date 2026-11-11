# KNIME no WaitOrBuy — como ele é usado

O KNIME faz uma tarefa real no projeto: **enviar, por e-mail, os jogos da lista de desejos que estão em bom preço**. Ele roda **sob demanda**: alguém abre o KNIME e executa o workflow `wf4_wishlist_email`. Não fica ligado o tempo todo e não faz parte do `docker compose`.

Os outros guias desta pasta: [COMO_FOI_FEITO.md](COMO_FOI_FEITO.md) (a montagem nó a nó e os problemas que apareceram) e [POR_QUE_INTEGRACAO.md](POR_QUE_INTEGRACAO.md) (por que ele conta como ferramenta de integração de dados). O roteiro original dos três workflows de coleta está em [BUILD_GUIDE.md](BUILD_GUIDE.md).

## O que ele faz, em uma frase
Para cada pessoa cadastrada, manda **um único e-mail** com **todos** os jogos da wishlist dela que estão em bom preço agora, cada um com loja e valor em R$ e um link para a página do jogo na WaitOrBuy. Quem não tem nenhum jogo em bom preço não recebe nada.

## Fluxo

```
KNIME (GET)  →  API /api/admin/wishlist-deals  →  lê wishlists (Firestore), preços (PostgreSQL) e aplica "vale esperar?"
     │                       │
     │            devolve um e-mail pronto por pessoa
     ▼
KNIME separa uma pessoa por vez (laço)  →  envia o e-mail (SMTP)  →  POST /api/admin/wishlist-deals/sent
                                                                       └ registra o aviso para não repetir
```

O KNIME **não calcula o preço bom**: quem decide é o backend, com a mesma regra da tela do jogo (veredito `COMPRAR_AGORA`, ver [docs/API.md](../docs/API.md)). Assim a regra fica em um lugar só.

## O que conta como "bom preço"
O veredito do jogo é `COMPRAR_AGORA`: o preço atual (a melhor oferta) está no menor preço histórico ou até 5% acima dele, e há pelo menos 5 dias de histórico. Preço estimado (`converted_usd`) e histórico simulado entram no e-mail, mas **sempre sinalizados** como tal.

## Como não repetir e-mail
Depois que o e-mail sai, o KNIME chama `POST /api/admin/wishlist-deals/sent`, e o backend grava `users/{uid}/wishlist_emails/{game_id}` no Firestore com o preço e a data. Um jogo só volta a ser avisado se:
- o preço cair abaixo do último preço avisado; ou
- passarem 30 dias do último aviso.

Se o envio falhar, o `POST` não é chamado e a pessoa continua pendente na próxima execução.

## Como executar

1. Suba a stack: `docker compose up -d --wait`.
2. Garanta que há alguém para receber. No terminal, com o `ADMIN_TOKEN` do seu `.env`:
   `curl.exe -H "X-Admin-Token: SEU_TOKEN" http://localhost:8001/api/admin/wishlist-deals`
   Deve voltar `"count": 1` ou mais. Se vier `0`, ninguém tem jogo em bom preço pendente.
3. Para testar sem enviar e-mail de verdade, suba o MailHog: `docker run --rm -p 1025:1025 -p 8025:8025 mailhog/mailhog` (caixa de entrada em http://localhost:8025) e use `localhost:1025` no nó *Send Email*.
4. Abra o KNIME Analytics Platform 5.x, abra o workflow `wf4_wishlist_email` (ou importe `knime/workflows/wf4_wishlist_email.knwf`).
5. Dê o token nos cabeçalhos `X-Admin-Token` do **GET Request** e do **POST Request**, e a senha SMTP no nó *Credentials Configuration* (ver abaixo).
6. Clique em **Execute all**.

### Reenviar para testar
Como o jogo já foi marcado como avisado, a segunda execução não envia nada (isso é o esperado). Para forçar um reenvio em teste, acrescente `?cooldown_days=0` na URL do GET Request:
`http://localhost:8001/api/admin/wishlist-deals?cooldown_days=0`
**Tire o parâmetro depois**, senão cada execução reenvia tudo.

## Configuração

| O quê | Onde | Observação |
|---|---|---|
| Token do admin | cabeçalho `X-Admin-Token` do GET e do POST | É o `ADMIN_TOKEN` do `.env`. **Nunca** exportar o workflow com ele preenchido. |
| Servidor SMTP de teste | nó *Send Email* | MailHog: `localhost`, porta `1025`, sem autenticação. |
| Servidor SMTP real | nó *Send Email* | Gmail: `smtp.gmail.com`, porta `587`, `STARTTLS`, autenticação ligada, usuário = o Gmail e senha = **senha de app** (https://myaccount.google.com/apppasswords, exige verificação em duas etapas). |
| Senha SMTP | nó *Credentials Configuration* (`smtp`) ou no próprio *Send Email* | Não vai para o git. Limpar antes de exportar. |
| Endereço do site nos links | `PUBLIC_URL` no `.env` | Sem ele, usa o primeiro de `FRONTEND_ORIGIN` (`http://localhost:5173`). Com `localhost`, o link só abre no computador onde a stack roda. |

## O que o e-mail contém
- Assunto: "WaitOrBuy: *Jogo* está em bom preço" (um jogo) ou "WaitOrBuy: N jogos da sua lista estão em bom preço".
- Uma tabela com jogo, preço em R$, loja e o link **"ver na WaitOrBuy"** (página do jogo na plataforma, não a loja).
- Avisos quando o preço é estimado ou o histórico é simulado.

## Problemas comuns

| Sintoma | Causa | Solução |
|---|---|---|
| `403 forbidden` no GET | token errado ou o backend não foi reiniciado depois de trocar o `.env` | conferir o valor e rodar `docker compose up -d --build` |
| `count: 0` | ninguém tem jogo em bom preço pendente, ou já foi avisado | testar com `?cooldown_days=0` |
| `Invalid Addresses ... <missing>` no Send Email | lista vazia: o laço rodou com valores ausentes | marcar *Skip empty collections* e *Skip missing values* no nó *Ungroup* |
| `Must issue a STARTTLS command first` | segurança do SMTP em `NONE` | usar `STARTTLS` na porta 587 |
| `535 Username and Password not accepted` | senha de app errada, ou não é a do Gmail do campo usuário | gerar outra senha de app |
| E-mail "não chegou" com MailHog | o MailHog **não entrega** para ninguém; só guarda na caixa local | abrir http://localhost:8025 ou trocar para SMTP real |

## Limites conhecidos
- Roda só quando alguém executa; não há agendamento (o KNIME Server/Hub, pago, permitiria).
- O link do e-mail aponta para `localhost` enquanto `PUBLIC_URL` não for o endereço público do site.
- Não foi testado com mais de uma pessoa ao mesmo tempo (ver [COMO_FOI_FEITO.md](COMO_FOI_FEITO.md)).

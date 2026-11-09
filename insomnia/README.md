# Testes no Insomnia

Coleção pronta para testar a API do WaitOrBuy: [waitorbuy.insomnia.json](waitorbuy.insomnia.json).

## 1. Subir o projeto

```bash
make up && make migrate && make etl && make seed-demo
python scripts/demo_user.py      # garante o usuário demo no emulador (demo@waitorbuy.test)
```

Confira em http://localhost:8000/health que os três bancos respondem.

## 2. Importar no Insomnia

`Create > Import > File` e escolha `insomnia/waitorbuy.insomnia.json`.

O ambiente já vem configurado (`Manage Environments`):

| Variável | Valor padrão |
|---|---|
| `base_url` | `http://localhost:8000` |
| `auth_url` | `http://localhost:9099` (Auth Emulator) |
| `admin_token` | `troque-este-token-admin` (igual ao `.env`) |
| `search_term` | `hades` |

`token`, `game_id`, `alert_id` e `notification_id` são preenchidos automaticamente a partir das respostas
de *Login*, *Buscar jogo*, *Alerta: criar* e *Notificações: listar*.

## 3. Testar

- **Manual:** abra as pastas e envie as requisições. Ordem do fluxo logado: *Login* → *Wishlist: adicionar* →
  *Alerta: criar* → *Admin: avaliar alertas* → *Notificações: listar* → *Marcar lida* → remover alerta/wishlist.
- **Automático:** aba **Test** do Insomnia, com 4 suítes (*Infra*, *Publico*, *Autenticacao*,
  *Fluxo do usuario*). Clique em *Run Tests* em cada uma.

Se uma requisição com `{{ _.token }}` falhar com 401, envie *Login usuario demo* de novo (o token do emulador expira em 1 h).
Se os testes de `req_notifications`/*Marcar lida* falharem por falta de notificação, rode *Admin: avaliar alertas* antes.

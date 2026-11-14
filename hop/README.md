# Apache Hop — integração visual

Pipeline `pipelines/wf2_fx.hpl`: **API do Banco Central (PTAX) → PostgreSQL**.

```
Montar URL → Consultar PTAX (REST GET) → Ler cotações (JSON) → Ajustar campos → Gravar exchange_rates (insert/update)
```

- Lê as cotações de compra e venda do período e grava em `exchange_rates` com upsert por `rate_date` (rodar de novo não duplica).
- Equivale ao job Python `etl/jobs/fx.py`; o ETL principal continua sendo o `etl-runner`.
- A conexão `waitorbuy` fica em `metadata/rdbms/waitorbuy.json` e usa variáveis (`DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS`), sem senha no repositório.

## Rodar

Com a stack no ar (`docker compose up -d --wait`):

```bash
bash scripts/hop_fx.sh        # últimos 45 dias
bash scripts/hop_fx.sh 10     # últimos 10 dias
```

O script sobe o container `apache/hop` na rede do compose, passa o período e as credenciais do `.env` e executa o pipeline sem interface.

## Editar na interface gráfica

Abra o `hop-gui` apontando para esta pasta (`pipelines/` e `metadata/`) e defina as variáveis acima.

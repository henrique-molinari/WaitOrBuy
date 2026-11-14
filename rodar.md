Na raiz do projeto (`waitorbuy`), com o Docker Desktop aberto. Não use `make`, porque ele não existe no seu Windows.

## Tudo de uma vez (API, front, bancos e ETL)

```bash
docker compose up -d --build --wait
```

- **Front:** http://localhost:5173
- **API:** http://localhost:8001 (documentação interativa em http://localhost:8001/docs)
- **Verificar:** `curl http://localhost:8001/health` deve devolver `{"status":"ok",...}`.

Use `--build` sempre que mudar código. As imagens copiam o repositório, então não há recarga automática.

## Só a API (com os bancos)

```bash
docker compose up -d --build --wait postgres mongo backend
```

Para ver os logs: `docker compose logs -f backend`.

Para o ETL de preços (opcional, o `etl-runner` já coleta a cada 4 h):

```bash
docker compose up -d etl-runner
docker compose exec -T etl-runner python -m etl.jobs.all
```

A primeira coleta completa leva cerca de 40 minutos, por causa das pausas entre chamadas às lojas.

## Só o front

**Com recarga automática (para desenvolver)**, com a API já no ar:

```bash
cd frontend
npm install
npm run dev
```

Abre em http://localhost:5173 e usa a API real em `localhost:8001`. Se o container do front estiver rodando, pare antes (`docker compose stop frontend`), senão a porta 5173 fica ocupada.

**Sem API nenhuma**, com dados fictícios:

```bash
cd frontend
npm run dev:mock
```

O login do modo mock é `demo@waitorbuy.test` / `demo-123456`.

## Parar e retomar

```bash
docker compose stop        # para tudo, mantém os dados
docker compose up -d       # volta
```

Não use `docker compose down -v`: ele apaga o histórico de preços coletado.

## Dois detalhes do seu computador

- O seu `.env` está no **Firebase real**, então o login usa contas de verdade. Não existe a conta demo nesse modo; crie uma pela tela **Criar conta**.
- Se a stack tiver parado depois de reiniciar o Docker Desktop (containers com `Exited`), o mesmo comando `docker compose up -d --wait` resolve.
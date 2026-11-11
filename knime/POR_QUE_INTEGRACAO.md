# Por que o KNIME é uma ferramenta de integração de dados neste projeto

O requisito é "1+ ferramenta de integração (Apache Hop ou KNIME)" e um "processo de integração/consolidação" ([docs/CHECKLIST_REQUISITOS.md](../docs/CHECKLIST_REQUISITOS.md), R2 e R6). Este documento mostra o que, no workflow `wf4_wishlist_email`, é integração de dados de fato, e onde estão os limites.

## O que o workflow integra

Ele junta, em um único processo repetível, dados que vivem em lugares diferentes:

| Origem | Dado | Como chega ao KNIME |
|---|---|---|
| PostgreSQL | melhor preço atual, histórico e estatísticas de cada jogo | via API do backend |
| Firestore | wishlist de cada usuário e registro de avisos já enviados | via API do backend |
| Firebase Auth | e-mail de cada usuário | via API do backend |
| Regra "vale esperar?" (backend) | veredito do jogo | via API do backend |

Destinos: **e-mail** (SMTP) para o usuário e **escrita de volta** na plataforma (`POST /sent`, que grava no Firestore).

O KNIME acessa esses dados pela **API REST** do backend, e não direto nos bancos. É uma escolha de projeto (ver [COMO_FOI_FEITO.md](COMO_FOI_FEITO.md)): o backend já consolida as fontes e aplica a regra, e o KNIME consome o resultado.

## Critérios de integração que ele cumpre

| Critério | Como o workflow cumpre |
|---|---|
| **Extração** de fonte externa | *GET Request* consome a API REST autenticada (`X-Admin-Token`). |
| **Transformação** | *JSON Path* extrai campos de um JSON aninhado; *Ungroup* achata listas; *Column Filter* seleciona colunas; o laço separa um registro por pessoa. |
| **Carga / entrega** em destino | *Send Email* entrega o resultado por SMTP; *POST Request* escreve de volta o que foi enviado. |
| **Consolidação de múltiplas fontes** | O e-mail une preço (PostgreSQL), lista de desejos (Firestore), e-mail da conta (Firebase Auth) e veredito em uma única mensagem por pessoa. |
| **Orquestração** em ordem e dependência | *Table Row to Variable Loop Start* → *Send Email* → *POST Request* → *Variable Loop End*; o registro só roda **depois** do envio. |
| **Idempotência** (rodar de novo não duplica) | O aviso gravado (`wishlist_emails`) impede reenvio, salvo queda de preço ou 30 dias. |
| **Tratamento de erro** | O envio só é registrado depois que o e-mail sai. No *POST Request*, os erros HTTP devem ficar em *Fail node* (configuração recomendada), para o laço parar se o registro falhar. |
| **Segredos fora do código** | Token e senha SMTP não ficam no repositório; ver [COMO_E_USADO.md](COMO_E_USADO.md). |
| **Processo visual e documentado** | O fluxo é um grafo de nós; os passos e a configuração estão em [COMO_FOI_FEITO.md](COMO_FOI_FEITO.md). |
| **Testado** | A regra de repetição, o texto do e-mail e a proteção por token têm testes automatizados ([tests/test_wishlist_digest.py](../tests/test_wishlist_digest.py)). |

## Por que o KNIME e não só código Python

O envio poderia ser um job Python (o `etl-runner` já faz coleta de preços). O KNIME entra porque:
- o processo (buscar → transformar → enviar → confirmar) fica **visível como um fluxo**, fácil de explicar e de alterar sem mexer no backend;
- é **executado sob demanda** por quem opera o projeto, o que combina com um aviso que o responsável quer disparar;
- separa a **regra** (backend, testável) da **orquestração e entrega** (KNIME).

## Relação com o Apache Hop e com o ETL em Python

- O **ETL em Python** (`etl/jobs/`) continua sendo a coleta de preços, câmbio e catálogo, rodando no Docker.
- O **Apache Hop** ([hop/README.md](../hop/README.md)) tem o pipeline da cotação PTAX → PostgreSQL.
- O **KNIME** cobre o outro lado: pegar o que já está consolidado e **entregar** ao usuário.

Os três juntos mostram o ciclo completo: entrada de dados externos (Python e Hop), consolidação (PostgreSQL, MongoDB, Firestore e API) e saída para o usuário (KNIME).

## Limites (para não dizer mais do que é)

- O KNIME **lê pela API**, não conecta nos bancos diretamente; as consultas e a regra "vale esperar?" rodam no backend.
- Executa **sob demanda**, sem agendamento (o KNIME Server/Hub, pago, permitiria).
- O arquivo `.knwf` ainda precisa ser exportado para `knime/workflows/` (pendência registrada em [COMO_FOI_FEITO.md](COMO_FOI_FEITO.md)).
- Os workflows 1 a 3 de [BUILD_GUIDE.md](BUILD_GUIDE.md) seguem como roteiro, não montados; o que está montado e testado é o `wf4_wishlist_email`.

# Briefing — WaitOrBuy

> Fonte da verdade do projeto. Em conflito entre este arquivo e outro, vale este.

## 1. Disciplina e entrega
Desafio Final de Integração de Dados. A equipe constrói uma solução baseada em dados que transforma dados de fontes diferentes em informação útil para decisão. Criatividade é critério central. A avaliação NÃO conta quantidade de tecnologias; conta qualidade: problema relevante, solução que faz sentido, uso inteligente dos dados, integração entre fontes, valor ao usuário, criatividade.

### Requisitos mínimos obrigatórios (todos devem ter evidência no repositório)
| # | Requisito | Como o WaitOrBuy atende |
|---|---|---|
| R1 | 3+ tecnologias de armazenamento | PostgreSQL, MongoDB, Firebase (Firestore) |
| R2 | 1+ ferramenta de integração (Hop ou KNIME) | KNIME (3 workflows) + jobs Python equivalentes |
| R3 | Consumo de 1+ API externa | CheapShark, Steam Store, RAWG, Banco Central (PTAX) |
| R4 | Backend em Python | FastAPI |
| R5 | Frontend em React | React + TypeScript + Recharts |
| R6 | Processo de integração/consolidação | preços de várias lojas + câmbio + catálogo + histórico numa visão única |
| R7 | Interface para visualizar/usar resultados | busca, lista ordenada, histórico, vale esperar, wishlist, alertas |
| R8 | Demonstração funcional | `make demo` + roteiro de 5 min |

### Entregáveis
1. Solução funcional (aplicação executando).
2. Apresentação de 5 min: problema, arquitetura, tecnologias, funcionalidades, integrações + demonstração prática.
3. Repositório com código organizado e documentado.

## 2. O produto
**WaitOrBuy**: o usuário digita o nome de um jogo e vê as lojas (Steam, Epic Games, GOG, Humble, Fanatical e outras que a CheapShark cobrir) ordenadas do menor ao maior preço, em reais. A plataforma guarda histórico de preços, avisa quando o jogo atingir o preço desejado e responde "vale esperar?".

Problema: o mesmo jogo tem preços diferentes em cada loja, descontos aparecem e somem rápido, e é difícil saber se uma promoção é boa ou se o jogo costuma ficar mais barato depois. Público: jogadores de PC (consoles ficam como evolução, pois não há API pública). Mercado: links de afiliado e parcerias com comunidades.

### Funcionalidades
1. Busca por nome com lojas ordenadas pelo menor preço em reais.
2. Histórico por loja, com menor preço registrado e média.
3. Indicador "vale esperar?" (preço atual × histórico × grandes promoções sazonais).
4. Wishlist e alerta de preço desejado (notificação quando o preço cair).
5. Preço por hora de jogo (preço ÷ tempo médio de jogo).
6. Comparação do custo total da wishlist: qual loja fica mais barata para o carrinho inteiro.

### Fontes de dados
| Fonte | Formato | Traz |
|---|---|---|
| CheapShark API | REST/JSON, sem chave | ofertas e preços (USD) de várias lojas de PC, lista de lojas, menor preço histórico |
| Steam Store API | REST/JSON, sem chave | preço em reais (região BR, `cc=br`) e detalhes |
| RAWG API | REST/JSON, chave gratuita | capa, gênero, nota, plataformas, tempo médio de jogo |
| Banco Central PTAX (Olinda) | REST/JSON | cotação do dólar para converter USD em BRL |
| Calendário de promoções | tabela interna | janelas das grandes liquidações sazonais |

### Arquitetura
Fontes → Integração (KNIME / jobs Python) → Armazenamento (PostgreSQL + MongoDB + Firebase) → API FastAPI → React + Recharts.
- Workflow 1: a cada poucas horas, CheapShark + Steam para os jogos acompanhados; grava o preço do dia por loja no PostgreSQL.
- Workflow 2: PTAX; atualiza a cotação usada na conversão.
- Workflow 3: RAWG; grava o documento de cada jogo no MongoDB.
- API: busca, conversão, ordenação, regra "vale esperar?", dispara alertas; usa Firebase para contas, wishlist e notificações.
- Docker Compose para ambiente reproduzível.

### Telas
Home (busca grande + jogos em promoção) · Resultado (lojas do mais barato ao mais caro, com link) · Página do jogo (gráfico de histórico, menor preço, média, vale esperar?, tempo médio de jogo, preço por hora) · Wishlist (alertas e custo total por loja) · Login/cadastro · Notificações.

### Criatividade (destacar na apresentação)
Responde se é o melhor momento de comprar (não só o menor preço de hoje); preço por hora de jogo compara jogos de tamanhos diferentes; alerta por preço-alvo; "melhor combinação" de lojas para a wishlist.

## 3. Roteiro da apresentação (5 min)
0:00–0:45 problema · 0:45–1:45 arquitetura (KNIME, três bancos, quatro APIs) · 1:45–4:00 demo (buscar, lista ordenada, histórico, vale esperar, criar alerta, ver notificação) · 4:00–5:00 afiliados e próximos passos (lojas de console).

## 4. Observações
- Lojas de console não têm API pública: fora do escopo, listadas como evolução.
- Hoje é novembro de 2026: a Black Friday está próxima, ótimo gancho de demonstração para o "vale esperar?". O cálculo de datas sazonais deve ser dinâmico (não fixar o ano).

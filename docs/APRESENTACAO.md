# Apresentação — WaitOrBuy (5 minutos)

Cronometragem (briefing): problema 0:00–0:45 · arquitetura 0:45–1:45 · demo 1:45–4:00 · afiliados e próximos passos 4:00–5:00. Passo a passo da demo: [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

## Slide 1 — Problema (0:00–0:45)
**Título:** "Vale comprar agora ou esperar?"
- O mesmo jogo tem preços diferentes em cada loja.
- Promoções aparecem e somem rápido; difícil saber se a oferta é boa.
- Fala: "Quem joga em PC compara lojas em várias abas e ainda duvida se a promoção é boa de verdade."

## Slide 2 — Solução e público (0:45–1:00)
- Busca por nome → lojas em R$ do mais barato ao mais caro; histórico; alerta; indicador "vale esperar?"; preço por hora; custo da wishlist por loja.
- Público: jogadores de PC (consoles ficam como evolução: sem API pública).

## Slide 3 — Arquitetura (1:00–1:45)
Diagrama de [ARCHITECTURE.md](ARCHITECTURE.md): **CheapShark, Steam, RAWG, Banco Central → integração (KNIME / jobs Python) → PostgreSQL + MongoDB + Firestore → API FastAPI → React**.
- Fala: "Cada banco tem um motivo: Postgres para a série temporal de preços, Mongo para documentos de catálogo, Firestore para dados e notificações por usuário."

## Slide 4 — Tecnologias e integrações (1:45–2:00)
- Quatro APIs externas; três bancos; ETL idempotente a cada 4 h; FastAPI + pydantic; Firebase Auth/Firestore; Docker Compose; testes com bancos reais (pytest).
- Integração: preço USD × cotação PTAX; Steam em BRL real; catálogo; calendário sazonal (Black Friday calculada).

## Slide 5 — Demonstração (2:00–4:00)
Seguir DEMO_SCRIPT: buscar → lista ordenada → jogo (gráfico, vale esperar) → login → wishlist → alerta → avaliação → notificação → carrinho.
Gancho: "A Black Friday é em 27/11: por isso o indicador manda esperar em jogos com preço bem acima do mínimo."

## Slide 6 — Criatividade (4:00–4:20)
Responde *quando* comprar, não só "qual o menor preço"; preço por hora compara jogos de tamanhos diferentes; alerta por preço-alvo; melhor combinação de lojas.

## Slide 7 — Honestidade dos dados (4:20–4:35)
Steam real, demais lojas estimadas; histórico inicial simulado e rotulado; catálogo de exemplo sem chave RAWG.

## Slide 8 — Afiliados e próximos passos (4:35–5:00)
- Receita: links de afiliado (`AFFILIATE_TAG` já aplicado nos links) e parcerias com comunidades.
- Próximos: lojas de console, afiliados reais, mais jogos, push (FCM), interface final.

**Observação:** o `.pptx` não foi gerado (corte previsto no escopo); o texto acima serve de base para os slides.

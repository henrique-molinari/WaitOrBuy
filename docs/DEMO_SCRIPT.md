# Roteiro da demonstração (≈ 2 min 15 s dentro dos 5 min)

**Antes:** `make demo` concluído; abra `http://localhost:5173` e `http://localhost:8000/docs` em abas. Login demo: `demo@waitorbuy.test` / `demo-123456`. Hoje (09/11/2026) a Black Friday é **27/11** e a Steam Autumn Sale começa em **25/11**.

| Tempo | Passo | Fala |
|---|---|---|
| 0:00 | Home: mostrar "Em promoção" | "O WaitOrBuy compara o mesmo jogo em várias lojas, em reais, e diz se vale esperar." |
| 0:15 | Buscar **Elden Ring** (9 ofertas) | "Lojas do mais barato ao mais caro. Repare na coluna origem: a Steam é preço real em R$; as demais são convertidas do dólar pela cotação do Banco Central, por isso estimadas." |
| 0:35 | Abrir **Cyberpunk 2077** | "Aqui o tempo médio de jogo vira preço por hora: R$ 7,69 por hora." |
| 0:50 | Gráfico: alternar 30/90/180 d | "Histórico por dia. Ele só acumula com o tempo, então para a demo foi simulado — o selo avisa." |
| 1:05 | Selo "Vale esperar? ESPERAR" | "Preço atual bem acima do mínimo e uma grande liquidação chegando: Autumn Sale em 16 dias e Black Friday em 18. O motivo cita números reais." |
| 1:20 | Contraste: **Disco Elysium** ou **Hogwarts Legacy** (COMPRAR_AGORA) | "Aqui o preço está no mínimo histórico: compre agora." |
| 1:35 | Entrar (demo) → Cyberpunk → **＋ Wishlist**; adicionar também Elden Ring e Hades | "Wishlist por usuário, no Firebase." |
| 1:50 | Em Elden Ring, alvo = preço atual + 10 → **Criar alerta** | "Alerta por preço-alvo." |
| 2:00 | Terminal: `make alerts-eval` (ou `docker compose exec backend python -m app.cli evaluate-alerts`) | "O ETL roda a cada 4 h e faz isso sozinho; aqui disparo na hora." |
| 2:08 | Sino 🔔 sobe para 1; abrir Notificações; marcar como lida | "Notificação em tempo real pelo listener do Firestore." |
| 2:15 | Wishlist: custo total por loja e melhor combinação | "Loja incompleta é sinalizada; a melhor combinação mostra a economia." |

## Plano B (sem internet / API fora)
- Antes: rodar `make demo` com internet pelo menos uma vez (ou usar o snapshot versionado).
- Sem internet: `make demo-offline` (restaura `db/demo_snapshot.sql`, catálogo vem de fixtures) e seguir o mesmo roteiro. **Fale:** "sem rede usamos a última coleta salva; os selos de estimado/simulado/exemplo continuam valendo."
- Preços do snapshot têm a data da coleta; o histórico simulado é regerado em relação a hoje por `make seed-demo`.

## Frases de transição
- Busca → jogo: "Agora o que importa: dá para comprar hoje?"
- Vale esperar → conta: "Vamos guardar para ser avisado."
- Notificação → carrinho: "E se eu quiser vários jogos de uma vez?"

## Frase de honestidade dos dados
"Steam é real em reais; as outras lojas são estimadas pelo dólar; o histórico inicial é simulado e rotulado; o catálogo usa dados de exemplo sem chave da RAWG."

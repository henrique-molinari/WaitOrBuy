O WaitOrBuy responde uma pergunta em duas palavras, COMPRE ou ESPERE, e a identidade existe para que essa resposta seja vista antes de ser lida. Quem bate o olho em um bloco verde-limão ao lado de um vermelho-etiqueta, sobre papel térmico, com algarismos condensados enormes, está no WaitOrBuy; qualquer um desses elementos fora do conjunto é outro produto.

## O que torna isto o WaitOrBuy

- Use o par veredito em todo lugar onde há decisão: `buy` (verde-limão) para COMPRE, `wait` (vermelho-etiqueta) para ESPERE. Nenhum outro componente usa esses dois preenchimentos.
- Componha o fundo como papel de recibo: `surface` no claro, `surface-raised` nos cartões, divisórias `hairline` entre linhas, cantos de `radius-md` e `radius-lg`. Sem sombras, sem degradês.
- Faça do preço o protagonista: `price-hero`, `price-lg` e `price-md` em `display` (Big Shoulders Display 800), uma vez por tela no tamanho `price-hero`.
- Desenhe gráficos de histórico como degraus retos em `chart-line` com o menor preço marcado pelo ponto `buy` com anel `ink`: é a marca W, a linha de preço, em escala de dado.
- Assine telas e materiais com o Wordmark (`WaitOrBuy`, exatamente nesta caixa) e a marca em `assets/Logos`.

## Voz e conteúdo

Fale em português do Brasil, direto e concreto, como alguém que já olhou as cinco lojas por você. Verbo no imperativo no que é ação ("Avisar quando chegar a R$ 45"), afirmação curta no que é veredito ("Menor preço em 14 meses").

- Escreva valores em reais com vírgula e símbolo: `R$ 59,90`. Nunca "BRL", nunca ponto decimal.
- Escreva o veredito com a palavra, em maiúsculas, dentro do selo: COMPRE AGORA, VALE ESPERAR. Fora do selo, frase normal: "Vale esperar: este jogo costuma cair 30% na promoção de inverno".
- Dê sempre o número que sustenta o veredito: o menor preço, a média, o desconto, a data da promoção anterior. Nunca "ótimo preço!" sem dado.
- Trate o jogador por "você", sem exclamação e sem gíria forçada. Sem emojis; use as formas geométricas da marca.
- Nomeie as lojas pelo nome (Steam, Epic Games, GOG, Humble, Fanatical), sem logotipos de terceiros.

## Cor

- Texto: `ink` sobre `surface` e `surface-raised`; apoio em `ink-muted`.
- COMPRE: selo e preenchimento `buy` com `on-buy`; texto e ícone avulsos em `buy-text`; fundo suave `buy-soft` para a loja vencedora e para alerta atingido.
- ESPERE: `wait` com `on-wait`; texto avulso em `wait-text`; fundo suave `wait-soft`.
- Nunca use `buy` como texto ou traço sobre o tema Papel (1,15:1); nunca use branco sobre `wait` (3,3:1). Sempre `on-buy` e `on-wait`.
- Borda de controle: `border-strong`. Foco: anel `focus` sólido de 3px, 2px de respiro.
- O tema Noite não é preto puro: é `surface` verde-preto com `ink` em osso; `buy` e `wait` ficam iguais nos dois temas.
- O par verde-limão e vermelho se distingue por luminosidade (14:1 de `ink` sobre `buy`, 5,5:1 sobre `wait`) e sempre vem com a palavra COMPRE ou ESPERE; não dependa só do matiz.

## Tipografia

- Preços e títulos: `display-xl`, `display-lg`, `display-md`, `price-hero`, `price-lg`, `price-md` em `display`.
- Interface: `body-lg`, `body`, `body-sm` e `label` em `sans` (Schibsted Grotesk).
- Dados e legendas: `data` e `data-caption` em `mono` (Martian Mono), para alinhar algarismos em tabelas; legendas em maiúsculas.
- As três famílias vêm do Google Fonts; carregue-as no consumidor e mantenha as pilhas de reserva de `type.families`.

## Espaço, forma e layout

- Espaçamento só pelos degraus `space-1` a `space-9`; padding de cartão `space-5`, lacuna entre linhas de loja `space-3`.
- Cantos: `radius-pill` para selo e interruptor, `radius-lg` para cartões, `radius-md` para botões e linhas, `radius-sm` para campos.
- Alinhe tudo à esquerda; o número e o veredito dividem a primeira linha da página, o histórico vem logo abaixo.
- Movimento: nenhum que não seja uma troca de estado de 120ms; o preço nunca anima contando.

## Iconografia

A marca não usa pacote de ícones nem emoji. Use poucas formas geométricas de traço de 3px, pontas retas: seta para baixo (COMPRE), duas barras (ESPERE) e o ponto do logo. Para qualquer outro ícone, escolha um conjunto de traço reto de 2px a 3px e sem preenchimento. Ícones herdam a cor de texto do contexto (`ink`, `buy-text`, `wait-text`).

## Componentes

- `Verdict`: selo COMPRE ou ESPERE.
- `StoreRow`: lista comparativa de lojas em reais.
- `PriceHistory`: histórico, média e menor preço.
- `TargetAlert`: preço desejado e notificação.
- `Wordmark`: o nome e a marca W.

Os componentes são HTML e CSS (`components/bundle.css`, classes `wob-*`); o consumidor fornece preços em reais já convertidos, nomes de loja e datas.

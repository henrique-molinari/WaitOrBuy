-- 001_init: esquema base do WaitOrBuy (PostgreSQL 16, SQL puro)
CREATE TABLE IF NOT EXISTS stores (
    store_id  smallint PRIMARY KEY,           -- id da CheapShark
    name      text NOT NULL,
    domain    text,
    is_active boolean NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS games (
    game_id             serial PRIMARY KEY,
    title               text NOT NULL,
    slug                text NOT NULL UNIQUE,
    cheapshark_game_id  text UNIQUE,
    steam_app_id        integer,
    rawg_id             integer,
    tracked             boolean NOT NULL DEFAULT false,
    created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS price_snapshots (
    snapshot_id       bigserial PRIMARY KEY,
    game_id           integer  NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
    store_id          smallint NOT NULL REFERENCES stores(store_id),
    snapshot_date     date NOT NULL,
    captured_at       timestamptz NOT NULL DEFAULT now(),
    price_brl         numeric(10,2) NOT NULL CHECK (price_brl >= 0),
    price_original    numeric(10,2) NOT NULL,
    currency_original char(3) NOT NULL,
    fx_rate           numeric(10,4),
    normal_price_brl  numeric(10,2),
    discount_pct      numeric(5,2) NOT NULL DEFAULT 0,
    deal_url          text,
    price_origin      text NOT NULL CHECK (price_origin IN ('steam_brl','converted_usd')),
    is_simulated      boolean NOT NULL DEFAULT false,
    UNIQUE (game_id, store_id, snapshot_date)
);
CREATE INDEX IF NOT EXISTS ix_snap_game_date ON price_snapshots (game_id, snapshot_date);

CREATE TABLE IF NOT EXISTS exchange_rates (
    rate_date     date PRIMARY KEY,
    usd_brl_buy   numeric(10,4) NOT NULL,
    usd_brl_sell  numeric(10,4) NOT NULL,
    source        text NOT NULL DEFAULT 'BCB PTAX',
    fetched_at    timestamptz NOT NULL DEFAULT now()
);

-- Janelas recorrentes de liquidação. Se `rule` não é nulo, a data é calculada (ex.: black_friday).
CREATE TABLE IF NOT EXISTS seasonal_sales (
    id                    serial PRIMARY KEY,
    name                  text NOT NULL UNIQUE,
    scope                 text NOT NULL,          -- steam | epic | all
    rule                  text,                   -- black_friday | cyber_monday | NULL
    start_month           smallint,
    start_day             smallint,
    end_month             smallint,
    end_day               smallint,
    typical_discount_note text,
    source_note           text NOT NULL DEFAULT 'Datas aproximadas: verificar calendário oficial da loja.'
);

INSERT INTO seasonal_sales (name, scope, rule, start_month, start_day, end_month, end_day, typical_discount_note) VALUES
 ('Steam Lunar New Year Sale', 'steam', NULL, 2, 9, 2, 16, 'descontos de 10% a 75% em títulos selecionados'),
 ('Steam Spring Sale',         'steam', NULL, 3, 19, 3, 26, 'liquidação grande; muitos títulos em 50% a 80%'),
 ('Steam Summer Sale',         'steam', NULL, 6, 25, 7, 9,  'maior liquidação do ano junto à de inverno; 50% a 90%'),
 ('Steam Autumn Sale',         'steam', NULL, 11, 25, 12, 1, 'liquidação de outono; costuma coincidir com a Black Friday'),
 ('Steam Winter Sale',         'steam', NULL, 12, 22, 1, 5,  'liquidação de fim de ano; mínimos históricos frequentes'),
 ('Epic Mega Sale',            'epic',  NULL, 5, 15, 6, 12, 'Epic Mega Sale com cupom de desconto extra'),
 ('Black Friday',              'all',   'black_friday', NULL, NULL, NULL, NULL, '4ª sexta de novembro; inicia a temporada de ofertas'),
 ('Cyber Monday',              'all',   'cyber_monday', NULL, NULL, NULL, NULL, 'segunda-feira seguinte à Black Friday')
ON CONFLICT (name) DO NOTHING;

-- Preço atual REAL (não simulado) mais recente por jogo e loja.
CREATE OR REPLACE VIEW v_latest_price AS
SELECT DISTINCT ON (p.game_id, p.store_id)
       p.game_id, p.store_id, s.name AS store_name, p.snapshot_date, p.captured_at,
       p.price_brl, p.normal_price_brl, p.discount_pct, p.deal_url, p.price_origin,
       p.price_original, p.currency_original, p.fx_rate
FROM price_snapshots p
JOIN stores s ON s.store_id = p.store_id
WHERE NOT p.is_simulated
ORDER BY p.game_id, p.store_id, p.snapshot_date DESC;

-- Melhor preço de cada dia (menor entre lojas).
CREATE OR REPLACE VIEW v_daily_best AS
SELECT game_id, snapshot_date, MIN(price_brl) AS best_price_brl
FROM price_snapshots
GROUP BY game_id, snapshot_date;

CREATE OR REPLACE VIEW v_price_stats AS
SELECT game_id,
       MIN(best_price_brl)                                                             AS min_price_brl,
       ROUND(AVG(best_price_brl), 2)                                                   AS avg_price_brl,
       ROUND(AVG(best_price_brl) FILTER (WHERE snapshot_date >= CURRENT_DATE - 90), 2) AS avg_90d_brl,
       COUNT(*)                                                                        AS points,
       MIN(snapshot_date)                                                              AS first_day
FROM v_daily_best
GROUP BY game_id;

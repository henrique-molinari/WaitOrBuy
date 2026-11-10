-- 003: Instant Gaming (preço real em BRL) + descoberta de jogos pela busca + índice do catálogo da Instant Gaming.
ALTER TABLE price_snapshots DROP CONSTRAINT IF EXISTS price_snapshots_price_origin_check;
ALTER TABLE price_snapshots ADD CONSTRAINT price_snapshots_price_origin_check
    CHECK (price_origin IN ('steam_brl','converted_usd','nuuvem_brl','instantgaming_brl'));

INSERT INTO stores (store_id, name, domain, is_active) VALUES (101, 'Instant Gaming', 'instant-gaming.com', true)
ON CONFLICT (store_id) DO UPDATE SET name = EXCLUDED.name, domain = EXCLUDED.domain, is_active = true;

ALTER TABLE games ADD COLUMN IF NOT EXISTS instant_gaming_url text;
ALTER TABLE games ADD COLUMN IF NOT EXISTS nuuvem_checked_at timestamptz;
ALTER TABLE games ADD COLUMN IF NOT EXISTS ig_checked_at timestamptz;
ALTER TABLE games ADD COLUMN IF NOT EXISTS discovered boolean NOT NULL DEFAULT false;  -- veio de uma busca, não do YAML

-- Índice (título normalizado → URL) montado a partir do sitemap oficial da Instant Gaming (declarado no robots.txt).
CREATE TABLE IF NOT EXISTS ig_catalog (
    ig_id      integer PRIMARY KEY,
    url        text NOT NULL,
    norm_title text NOT NULL,
    platform   text NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ig_catalog_title ON ig_catalog (norm_title);

CREATE TABLE IF NOT EXISTS etl_meta (
    key        text PRIMARY KEY,
    value      text,
    updated_at timestamptz NOT NULL DEFAULT now()
);

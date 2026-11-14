-- Nuuvem: preço real em BRL lido da página do produto.
ALTER TABLE price_snapshots DROP CONSTRAINT IF EXISTS price_snapshots_price_origin_check;
ALTER TABLE price_snapshots ADD CONSTRAINT price_snapshots_price_origin_check
    CHECK (price_origin IN ('steam_brl','converted_usd','nuuvem_brl'));
INSERT INTO stores (store_id, name, domain, is_active) VALUES (100, 'Nuuvem', 'nuuvem.com', true)
ON CONFLICT (store_id) DO UPDATE SET name = EXCLUDED.name, domain = EXCLUDED.domain, is_active = true;
ALTER TABLE games ADD COLUMN IF NOT EXISTS nuuvem_slug text;

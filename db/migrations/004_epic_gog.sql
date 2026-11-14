-- 004: Epic e GOG com preço real em BRL (substituem a estimativa da CheapShark quando a loja responde).
ALTER TABLE price_snapshots DROP CONSTRAINT IF EXISTS price_snapshots_price_origin_check;
ALTER TABLE price_snapshots ADD CONSTRAINT price_snapshots_price_origin_check
    CHECK (price_origin IN ('steam_brl','converted_usd','nuuvem_brl','instantgaming_brl','epic_brl','gog_brl'));
ALTER TABLE games ADD COLUMN IF NOT EXISTS epic_slug text;
ALTER TABLE games ADD COLUMN IF NOT EXISTS epic_checked_at timestamptz;
ALTER TABLE games ADD COLUMN IF NOT EXISTS gog_id bigint;
ALTER TABLE games ADD COLUMN IF NOT EXISTS gog_slug text;
ALTER TABLE games ADD COLUMN IF NOT EXISTS gog_checked_at timestamptz;

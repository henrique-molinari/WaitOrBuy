-- 009: índice do catálogo da Nuuvem (sitemap oficial) e controle de nova checagem de Steam/CheapShark para jogos achados em outras lojas.
CREATE TABLE IF NOT EXISTS nuuvem_catalog (
    slug       text PRIMARY KEY,
    norm_title text NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_nuuvem_catalog_title ON nuuvem_catalog (norm_title text_pattern_ops);
CREATE INDEX IF NOT EXISTS ix_ig_catalog_title_prefix ON ig_catalog (norm_title text_pattern_ops);
ALTER TABLE games ADD COLUMN IF NOT EXISTS steam_checked_at timestamptz;
ALTER TABLE games ADD COLUMN IF NOT EXISTS cs_checked_at timestamptz;

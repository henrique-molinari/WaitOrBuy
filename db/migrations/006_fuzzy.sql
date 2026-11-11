-- 006: busca tolerante a erro de digitação ("wicther" encontra "The Witcher 3").
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- unaccent não é IMMUTABLE; este invólucro é o jeito padrão de usá-lo em expressões.
CREATE OR REPLACE FUNCTION wob_unaccent(text) RETURNS text
    LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
    AS $$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$;

-- Texto de comparação: minúsculo, sem acento, só letras/números separados por um espaço ("Marvel's Spider-Man" → "marvels spider man").
CREATE OR REPLACE FUNCTION wob_norm(text) RETURNS text
    LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
    AS $$ SELECT btrim(regexp_replace(regexp_replace(lower(wob_unaccent($1)), '[''’`´]', '', 'g'), '[^a-z0-9]+', ' ', 'g')) $$;

CREATE INDEX IF NOT EXISTS games_title_trgm ON games USING gin (wob_norm(title) gin_trgm_ops);

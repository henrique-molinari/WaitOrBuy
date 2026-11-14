-- 008: jogos populares da Steam que o job não conseguiu cadastrar (grátis, sem preço, DLC, não é PC). Evita tentar todo dia.
CREATE TABLE IF NOT EXISTS popular_skip (
    steam_app_id integer PRIMARY KEY,
    reason       text NOT NULL,
    skipped_at   timestamptz NOT NULL DEFAULT now()
);

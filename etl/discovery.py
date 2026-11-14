"""Descoberta sob demanda: a busca encontra QUALQUER jogo de PC vendido nas lojas conectadas, não só os do YAML.

Fluxo: a consulta vai a CheapShark, Steam, Epic e GOG (cada fonte pode falhar sozinha) → os títulos são unificados (a mesma obra em
várias lojas vira um candidato) → os ainda desconhecidos são cadastrados e precificados em paralelo (Steam/Epic/GOG/Nuuvem/Instant
Gaming/CheapShark) → metadados no Mongo. Jogo sem nenhuma oferta é descartado (não polui o catálogo).
"""
import logging
import re
import zlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from etl import config, fx
from etl.clients import epic, gog, steam
from etl.clients.cheapshark import CheapSharkClient
from etl.db import connect, mongo_games
from etl.http import HttpClient, RateLimited
from etl.jobs import catalog, seed_demo
from etl.jobs.prices import GAME_COLS, refresh_game
from etl.matching import norm, title_matches

log = logging.getLogger("etl.discovery")
MAX_NEW = 8      # jogos novos cadastrados por busca
WORKERS = 8      # jogos precificados ao mesmo tempo


# Fontes que só vendem PC: a Humble e a Nuuvem também vendem jogos de Nintendo Switch, então só elas não provam que é jogo de PC.
PC_ORIGINS = ("steam_brl", "epic_brl", "gog_brl", "instantgaming_brl")


def clean_title(t: str) -> str:
    """Tira ™ ® © e espaços estranhos que as lojas põem no nome ("Mortal Kombat™ 11" → "Mortal Kombat 11")."""
    return re.sub(r"\s+", " ", re.sub(r"[™®©℠]", "", (t or "").replace(" ", " "))).strip()


@dataclass
class Candidate:
    title: str
    cheapshark_id: str | None = None
    steam_id: int | None = None


def _rank(query: str, title: str) -> tuple:
    q, t = norm(query), norm(title)
    return (t != q, not t.startswith(q), len(t))


def relevant(query: str, titles: list[str]) -> list[str]:
    """Mantém só títulos que contêm todas as palavras da busca (sem acento); melhor primeiro (exato, prefixo, mais curto)."""
    words = norm(query).split()
    # cada palavra da busca tem de abrir alguma palavra do título ("nier" não casa com "Tavernier"; "witch" casa com "Witcher")
    ok = [t for t in titles if all(any(tok.startswith(w) for tok in norm(t).split()) for w in words)]
    return sorted(ok, key=lambda t: _rank(query, t))


def _same_game(a: str, b: str) -> bool:
    return title_matches(a, b) or title_matches(b, a)


def merge(candidates: list[Candidate]) -> list[Candidate]:
    """A mesma obra vinda de lojas diferentes (ou numa edição) vira um candidato só, guardando todos os ids conhecidos."""
    out: list[Candidate] = []
    for c in candidates:
        for m in out:
            if _same_game(m.title, c.title):
                m.cheapshark_id = m.cheapshark_id or c.cheapshark_id
                m.steam_id = m.steam_id or c.steam_id
                break
        else:
            out.append(Candidate(c.title, c.cheapshark_id, c.steam_id))
    return out


def gather(http: HttpClient, query: str) -> tuple[list[Candidate], int]:
    """Candidatos de todas as fontes e quantas fontes falharam. Steam primeiro (nome canônico e id), depois Epic, GOG e CheapShark."""
    def steam_src(h):
        return [Candidate(r["name"], steam_id=r["id"]) for r in steam.search(h, query)]

    def cheapshark_src(h):
        return [Candidate(x.external, cheapshark_id=x.gameID, steam_id=int(x.steamAppID) if x.steamAppID and x.steamAppID.isdigit() else None)
                for x in CheapSharkClient(h).search(query, limit=12)]

    sources = (("steam", steam_src), ("epic", lambda h: [Candidate(t) for t in epic.search_titles(h, query)]),
               ("gog", lambda h: [Candidate(t) for t in gog.search_titles(h, query)]), ("cheapshark", cheapshark_src))

    def run_source(item):
        name, fetch = item
        try:
            return [Candidate(clean_title(c.title), c.cheapshark_id, c.steam_id) for c in fetch(http.clone())], False
        except Exception as exc:  # uma loja fora do ar não impede as outras
            log.warning("busca em %s falhou para %r: %s", name, query, exc)
            return [], True

    with ThreadPoolExecutor(max_workers=len(sources)) as pool:  # as 4 lojas são consultadas ao mesmo tempo (ordem do resultado preservada)
        outcomes = list(pool.map(run_source, sources))
    found = [c for cands, _ in outcomes for c in cands]
    failed = sum(1 for _, bad in outcomes if bad)
    keep = set(relevant(query, [c.title for c in found]))
    return merge([c for c in found if c.title in keep]), failed


def _known(conn) -> tuple[set, set, list[str]]:
    rows = conn.execute("SELECT title, cheapshark_game_id, steam_app_id FROM games").fetchall()
    return ({r["cheapshark_game_id"] for r in rows if r["cheapshark_game_id"]}, {r["steam_app_id"] for r in rows if r["steam_app_id"]},
            [r["title"] for r in rows])


def _slug_for(conn, title: str, suffix: str) -> str:
    slug = config.slugify(title) or f"jogo-{suffix}"
    if conn.execute("SELECT 1 FROM games WHERE slug = %s", (slug,)).fetchone():
        slug = f"{slug}-{suffix}"
    return slug


def _create(c: Candidate, http: HttpClient, rate: float, active: set, today, coll) -> int | None:
    """Cadastra e precifica um candidato (conexão própria, para rodar em thread). Devolve o game_id ou None se não rendeu oferta."""
    http = http.clone()
    with connect() as conn:
        if c.steam_id:  # a busca da Steam também devolve DLC e trilhas: só jogo-base entra
            meta = steam.fetch_meta(http, c.steam_id)
            if meta is None or (meta.get("type") and meta["type"] != "game"):
                return None
        suffix = c.cheapshark_id or str(c.steam_id or zlib.crc32(norm(c.title).encode()) % 100000)
        row = conn.execute(
            "INSERT INTO games (title, slug, cheapshark_game_id, steam_app_id, tracked, discovered) VALUES (%s, %s, %s, %s, true, true) "
            "ON CONFLICT (slug) DO NOTHING RETURNING game_id", (c.title, _slug_for(conn, c.title, suffix), c.cheapshark_id, c.steam_id)).fetchone()
        conn.commit()
        if not row:  # outra busca cadastrou o mesmo jogo agora há pouco
            return None
        stats = {"snapshots": 0}
        g = conn.execute(f"SELECT {GAME_COLS}, slug FROM games WHERE game_id = %s", (row["game_id"],)).fetchone()
        try:
            refresh_game(conn, http, CheapSharkClient(http), g, rate, active, today, stats)
        except RateLimited:
            conn.rollback()
            stats["snapshots"] = 0
        except Exception as exc:
            log.error("descoberta falhou em %s: %s", c.title, exc)
            conn.rollback()
            stats["snapshots"] = 0
        is_pc = conn.execute("SELECT 1 FROM price_snapshots WHERE game_id = %s AND price_origin = ANY(%s) LIMIT 1",
                             (row["game_id"], list(PC_ORIGINS))).fetchone()
        if not stats["snapshots"] or not is_pc:  # sem oferta, ou sem prova de que é jogo de PC (ex.: só Switch na Humble)
            conn.execute("DELETE FROM games WHERE game_id = %s", (row["game_id"],))
            conn.commit()
            return None
        try:  # histórico inicial SIMULADO (is_simulated=true, sinalizado na tela) para o gráfico e o veredito não nascerem vazios
            seed_demo.run(conn, today, game_ids=[row["game_id"]])
        except Exception as exc:
            log.error("histórico inicial de %s falhou: %s", c.title, exc)
            conn.rollback()
        try:
            doc = catalog.build_doc(g, {}, http, config.RAWG_API_KEY)
            catalog.save_doc(conn, coll, g, doc)
            conn.commit()
        except Exception as exc:  # metadados são opcionais: o jogo continua com preços
            log.error("metadados de %s falharam: %s", c.title, exc)
        return row["game_id"]


def discover(conn, http: HttpClient, query: str, max_new: int = MAX_NEW, coll=None) -> list[int]:
    """Cadastra e precifica até `max_new` jogos ainda desconhecidos que combinam com a busca. Devolve os game_id novos.
    Levanta RuntimeError se NENHUMA fonte respondeu (a busca então avisa o usuário)."""
    candidates, failed = gather(http, query)
    if failed >= 4:
        raise RuntimeError("nenhuma loja respondeu à busca")
    created = register(conn, http, candidates, max_new, coll)
    log.info("descoberta %r: %d jogos cadastrados", query, len(created))
    return created


def register(conn, http: HttpClient, candidates: list[Candidate], max_new: int = MAX_NEW, coll=None) -> list[int]:
    """Cadastra e precifica até `max_new` candidatos que o banco ainda não conhece. Devolve os game_id novos."""
    cs_ids, steam_ids, titles = _known(conn)
    todo = [c for c in candidates if not ((c.cheapshark_id and c.cheapshark_id in cs_ids) or (c.steam_id and c.steam_id in steam_ids)
                                          or any(_same_game(t, c.title) for t in titles))][:max_new]
    if not todo:
        return []
    found = fx.rate_from_db(conn, config.today_br())
    if not found:
        return []
    _, rate = found
    active = {r["store_id"] for r in conn.execute("SELECT store_id FROM stores WHERE is_active")}
    coll = coll if coll is not None else mongo_games()
    today = config.today_br()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(lambda c: _create(c, http, rate, active, today, coll), todo))
    return [r for r in results if r]


def run(query: str) -> list[int]:
    with connect() as conn:
        return discover(conn, HttpClient(pause=0.3, retries=1), query)

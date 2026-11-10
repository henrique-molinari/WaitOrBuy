"""Casamento de títulos entre lojas: igual, ou o mesmo jogo numa edição ("Remastered", "GOTY"...). Nunca uma sequência ou DLC."""
import re
import unicodedata

# Palavras que só indicam a edição do MESMO jogo; qualquer outra sobra (ex.: "ii", "soundtrack") significa outro produto.
EDITION_WORDS = {"remastered", "remaster", "goty", "game", "of", "the", "year", "edition", "complete", "definitive", "enhanced", "deluxe",
                 "directors", "director", "s", "cut", "ultimate", "gold", "special", "anniversary", "legendary", "standard", "final",
                 "digital", "premium", "collection", "base", "pc"}


def norm(s: str) -> str:
    """Minúsculas, sem acento nem pontuação: "Pokémon: Edição" → "pokemon edicao"."""
    plain = unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()
    plain = re.sub(r"['’`´]", "", plain)  # "Baldur's" e "Baldurs" são o mesmo título; as lojas divergem na pontuação
    return re.sub(r"[^a-z0-9]+", " ", plain).strip()


def title_matches(wanted: str, found: str) -> bool:
    w, f = norm(wanted), norm(found)
    if not w or not f:
        return False
    if f == w:
        return True
    if not f.startswith(w + " "):
        return False
    return all(tok in EDITION_WORDS for tok in f[len(w):].split())


def best_match(wanted: str, candidates: list, key):
    """Candidato cujo título (via `key`) casa com `wanted`: o igual primeiro, senão o de título mais curto. None se nenhum casa."""
    ok = [c for c in candidates if title_matches(wanted, key(c))]
    if not ok:
        return None
    return sorted(ok, key=lambda c: (norm(key(c)) != norm(wanted), len(norm(key(c)))))[0]

"""Executa os jobs em ordem: câmbio → índices Instant Gaming e Nuuvem → preços → catálogo."""
import logging

from etl.jobs import catalog, fx, ig_index, nuuvem_index, popular, prices


def run() -> dict:
    out = {"fx": fx.run()}
    try:
        out["ig_index"] = ig_index.run()
    except Exception as exc:  # índice é opcional: sem ele só a Instant Gaming fica de fora
        out["ig_index"] = {"error": str(exc)}
    try:
        out["nuuvem_index"] = nuuvem_index.run()
    except Exception as exc:  # idem: sem o índice a Nuuvem cai nos palpites de slug
        out["nuuvem_index"] = {"error": str(exc)}
    out["prices"] = prices.run()
    out["catalog"] = catalog.run()
    try:
        out["popular"] = popular.run()
    except Exception as exc:  # catálogo inicial é opcional: falha aqui não derruba o ciclo
        out["popular"] = {"error": str(exc)}
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())

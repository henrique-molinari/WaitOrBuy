"""Executa os jobs em ordem: câmbio → índice Instant Gaming → preços → catálogo."""
import logging

from etl.jobs import catalog, fx, ig_index, prices


def run() -> dict:
    out = {"fx": fx.run()}
    try:
        out["ig_index"] = ig_index.run()
    except Exception as exc:  # índice é opcional: sem ele só a Instant Gaming fica de fora
        out["ig_index"] = {"error": str(exc)}
    out["prices"] = prices.run()
    out["catalog"] = catalog.run()
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())

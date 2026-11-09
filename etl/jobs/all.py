"""Executa os três jobs em ordem: câmbio → preços → catálogo."""
import logging

from etl.jobs import catalog, fx, prices


def run() -> dict:
    out = {"fx": fx.run()}
    out["prices"] = prices.run()
    out["catalog"] = catalog.run()
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())

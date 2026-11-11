"""Gera 180 dias de histórico SIMULADO (is_simulated=true) a partir do preço atual real. Determinístico e idempotente.

O histórico real só acumula com o tempo; este seed existe para a demonstração. Nunca sobrescreve dado real.
"""
import logging
import random
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from etl import config
from etl.db import connect

log = logging.getLogger("etl.jobs.seed_demo")
DAYS = 180

UPSERT = """
INSERT INTO price_snapshots (game_id, store_id, snapshot_date, captured_at, price_brl, price_original,
    currency_original, fx_rate, normal_price_brl, discount_pct, deal_url, price_origin, is_simulated)
VALUES (%(game_id)s, %(store_id)s, %(d)s, now(), %(price_brl)s, %(price_original)s, %(currency)s, %(fx_rate)s,
    %(normal)s, %(discount)s, %(deal_url)s, %(origin)s, true)
ON CONFLICT (game_id, store_id, snapshot_date) DO UPDATE SET
    price_brl = EXCLUDED.price_brl, price_original = EXCLUDED.price_original, normal_price_brl = EXCLUDED.normal_price_brl,
    discount_pct = EXCLUDED.discount_pct, fx_rate = EXCLUDED.fx_rate, deal_url = EXCLUDED.deal_url
WHERE price_snapshots.is_simulated
"""


def in_window(d: date, sm: int, sd: int, em: int, ed: int) -> bool:
    key, start, end = (d.month, d.day), (sm, sd), (em, ed)
    return start <= key <= end if start <= end else (key >= start or key <= end)  # janela que vira o ano


def game_discount(game_id: int, d: date, windows: list[dict]) -> float:
    """Desconto (0..1) do jogo no dia d: liquidações sazonais + promoções curtas aleatórias porém determinísticas."""
    best = 0.0
    for w in windows:
        if in_window(d, w["start_month"], w["start_day"], w["end_month"], w["end_day"]):
            r = random.Random(f"{game_id}:{w['id']}:{d.year}")
            best = max(best, r.uniform(0.25, 0.60) if r.random() < 0.85 else 0.0)
    block = d.toordinal() // 14
    r = random.Random(f"{game_id}:{block}")
    if r.random() < 0.35:
        start = block * 14 + r.randint(0, 9)
        length = r.randint(3, 6)
        if start <= d.toordinal() < start + length:
            best = max(best, r.uniform(0.10, 0.40))
    return best


def simulate_price(game_id: int, store_id: int, d: date, normal: Decimal, windows: list[dict]) -> Decimal:
    disc = game_discount(game_id, d, windows)
    noise = random.Random(f"{game_id}:{store_id}:{d.toordinal()}").uniform(-0.02, 0.02)
    price = normal * Decimal(str(round((1 - disc) * (1 + noise), 4)))
    return max(price, normal * Decimal("0.1")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def run(conn=None, today: date | None = None, game_ids: list[int] | None = None) -> dict:
    own = conn is None
    conn = conn or connect()
    today = today or config.today_br()
    try:
        windows = conn.execute(
            "SELECT id, start_month, start_day, end_month, end_day FROM seasonal_sales WHERE rule IS NULL"
        ).fetchall()
        current = conn.execute(
            "SELECT l.* FROM v_latest_price l JOIN games g USING (game_id) WHERE g.tracked AND (%s::int[] IS NULL OR g.game_id = ANY(%s)) ORDER BY game_id, store_id",
            (game_ids, game_ids)).fetchall()
        rows = 0
        games = set()
        for c in current:
            normal = c["normal_price_brl"] or c["price_brl"]
            games.add(c["game_id"])
            batch = []
            for back in range(1, DAYS + 1):
                d = today - timedelta(days=back)
                price = simulate_price(c["game_id"], c["store_id"], d, normal, windows)
                converted = c["price_origin"] == "converted_usd"
                fx_rate = c["fx_rate"]
                original = (price / fx_rate).quantize(Decimal("0.01")) if converted and fx_rate else price
                disc = round((1 - price / normal) * 100, 2) if normal else 0
                batch.append({
                    "game_id": c["game_id"], "store_id": c["store_id"], "d": d, "price_brl": price,
                    "price_original": original, "currency": "USD" if converted else "BRL", "fx_rate": fx_rate,
                    "normal": normal, "discount": disc, "deal_url": c["deal_url"], "origin": c["price_origin"],
                })
            with conn.cursor() as cur:
                cur.executemany(UPSERT, batch)
            rows += len(batch)
        conn.commit()
        log.info("seed_demo: %d linhas simuladas para %d jogos", rows, len(games))
        return {"games": len(games), "rows_upserted": rows}
    finally:
        if own:
            conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())

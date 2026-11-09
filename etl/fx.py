"""Conversão USD→BRL com a cotação de venda PTAX; fim de semana/feriado usa a última cotação disponível."""
from datetime import date
from decimal import ROUND_HALF_UP, Decimal


def to_brl(usd: Decimal, rate: Decimal) -> Decimal:
    return (Decimal(usd) * Decimal(rate)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def pick_rate(rates: dict[date, Decimal], on: date) -> tuple[date, Decimal] | None:
    """Última cotação com rate_date <= on (puro, para teste)."""
    eligible = [d for d in rates if d <= on]
    if not eligible:
        return None
    d = max(eligible)
    return d, rates[d]


def rate_from_db(conn, on: date) -> tuple[date, Decimal] | None:
    row = conn.execute(
        "SELECT rate_date, usd_brl_sell FROM exchange_rates WHERE rate_date <= %s ORDER BY rate_date DESC LIMIT 1", (on,)
    ).fetchone()
    return (row["rate_date"], row["usd_brl_sell"]) if row else None

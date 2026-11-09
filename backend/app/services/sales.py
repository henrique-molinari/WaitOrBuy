"""Liquidações sazonais: janelas recorrentes (tabela seasonal_sales) e Black Friday/Cyber Monday calculadas."""
from datetime import date, timedelta


def black_friday(year: int) -> date:
    """4ª sexta-feira de novembro."""
    first = date(year, 11, 1)
    first_friday = first + timedelta(days=(4 - first.weekday()) % 7)
    return first_friday + timedelta(weeks=3)


def cyber_monday(year: int) -> date:
    return black_friday(year) + timedelta(days=3)


def _windows(row: dict, year: int) -> tuple[date, date]:
    rule = row.get("rule")
    if rule == "black_friday":
        s = black_friday(year)
        return s, s + timedelta(days=2)
    if rule == "cyber_monday":
        s = cyber_monday(year)
        return s, s
    start = date(year, row["start_month"], row["start_day"])
    end_year = year + 1 if (row["end_month"], row["end_day"]) < (row["start_month"], row["start_day"]) else year
    return start, date(end_year, row["end_month"], row["end_day"])


def next_sale(today: date, rows: list[dict], ignore: tuple[str, ...] = ()) -> dict | None:
    """Liquidação em andamento (days=0) ou a próxima. Considera virada de ano."""
    best = None
    for row in rows:
        if row["name"] in ignore:
            continue
        for year in (today.year - 1, today.year, today.year + 1):
            start, end = _windows(row, year)
            if end < today:
                continue
            days = max((start - today).days, 0)
            if best is None or days < best["days"]:
                best = {"name": row["name"], "start_date": start, "end_date": end, "days": days,
                        "note": "verificar calendário oficial", "scope": row["scope"]}
            break
    return best

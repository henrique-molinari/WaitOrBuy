from datetime import date

import pytest

from app.services.verdict import VerdictInput, confidence, evaluate

SALE = date(2026, 11, 27)


def mk(**kw):
    base = dict(price_now=100.0, min_ever=80.0, avg_all=100.0, avg_90d=100.0, discount_pct=0.0,
                days_to_next_sale=None, sale_name=None, sale_date=None, history_days=100)
    base.update(kw)
    return VerdictInput(**base)


SALE_KW = dict(days_to_next_sale=18, sale_name="Black Friday", sale_date=SALE)

CASES = [
    # nome, entrada, veredito esperado
    ("A: exatamente 1,05x mínimo", mk(price_now=84.0), "COMPRAR_AGORA"),
    ("A: acima de 1,05x (84,01) cai para outra regra", mk(price_now=84.01, avg_90d=200.0), "NEUTRO"),
    ("A: preço igual ao mínimo", mk(price_now=80.0, min_ever=80.0), "COMPRAR_AGORA"),
    ("A vence B mesmo com liquidação próxima", mk(price_now=80.0, **SALE_KW), "COMPRAR_AGORA"),
    ("B: 1,15x exato NÃO espera", mk(price_now=92.0, avg_90d=500.0, **SALE_KW), "NEUTRO"),
    ("B: acima de 1,15x com liquidação em 18 dias", mk(price_now=92.01, **SALE_KW), "ESPERAR"),
    ("B: liquidação em exatamente 30 dias", mk(price_now=100.0, days_to_next_sale=30, sale_name="X", sale_date=SALE), "ESPERAR"),
    ("B: liquidação em 31 dias não conta", mk(price_now=100.0, avg_90d=500.0, days_to_next_sale=31, sale_name="X", sale_date=SALE), "NEUTRO"),
    ("B: liquidação virando o ano (em andamento, 0 dias)", mk(price_now=100.0, days_to_next_sale=0, sale_name="Steam Winter Sale", sale_date=date(2026, 12, 22)), "ESPERAR"),
    ("C: 0,95x média 90d exato, desconto 19,99", mk(price_now=95.0, avg_90d=100.0, discount_pct=19.99), "ESPERAR"),
    ("C: abaixo de 0,95x média", mk(price_now=94.99, avg_90d=100.0, discount_pct=0), "NEUTRO"),
    ("C: desconto exatamente 20% não espera", mk(price_now=100.0, avg_90d=100.0, discount_pct=20.0), "NEUTRO"),
    ("C: bloqueado por liquidação em até 30 dias (cai em B se > 1,15x)", mk(price_now=100.0, avg_90d=100.0, **SALE_KW), "ESPERAR"),
    ("C: sem média 90d não dispara", mk(price_now=100.0, avg_90d=None), "NEUTRO"),
    ("D: neutro", mk(price_now=90.0, avg_90d=100.0, discount_pct=30), "NEUTRO"),
    ("INSUFICIENTE: 4 dias", mk(history_days=4, price_now=80.0), "INSUFICIENTE"),
    ("5 dias já avalia", mk(history_days=5, price_now=80.0), "COMPRAR_AGORA"),
    ("INSUFICIENTE: sem mínimo", mk(min_ever=None), "INSUFICIENTE"),
    ("INSUFICIENTE: sem preço atual", mk(price_now=None), "INSUFICIENTE"),
]


@pytest.mark.parametrize("name,inp,expected", CASES, ids=[c[0] for c in CASES])
def test_verdict_table(name, inp, expected):
    out = evaluate(inp)
    assert out["verdict"] == expected
    assert out["reasons"], "todo veredito precisa de motivos"


@pytest.mark.parametrize("days,expected", [(0, "baixa"), (13, "baixa"), (14, "media"), (90, "media"), (91, "alta")])
def test_confidence_bounds(days, expected):
    assert confidence(days) == expected


def test_reason_cites_sale_name_and_date():
    out = evaluate(mk(price_now=100.0, **SALE_KW))
    text = " ".join(out["reasons"])
    assert "Black Friday" in text and "27/11/2026" in text and "R$ 80,00" in text


def test_metrics_exposed():
    out = evaluate(mk())
    assert out["metrics"]["min_ever"] == 80.0 and out["metrics"]["history_days"] == 100

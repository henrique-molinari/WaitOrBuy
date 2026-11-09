"""Indicador "vale esperar?": determinístico e explicável. Limiares em app.config.VERDICT."""
from dataclasses import dataclass
from datetime import date

from app.config import VERDICT, VerdictConfig


def brl(v: float) -> str:
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _lim(factor: float, base: float) -> float:
    """Limite em centavos: evita erro de ponto flutuante nos extremos (ex.: 1,15 × 80 = 92,00)."""
    return round(factor * base, 2)


@dataclass
class VerdictInput:
    price_now: float | None
    min_ever: float | None
    avg_all: float | None
    avg_90d: float | None
    discount_pct: float | None
    days_to_next_sale: int | None   # só liquidações "grandes"
    sale_name: str | None
    sale_date: date | None
    history_days: int


def confidence(history_days: int, cfg: VerdictConfig = VERDICT) -> str:
    if history_days < cfg.confidence_low_days:
        return "baixa"
    if history_days <= cfg.confidence_high_days:
        return "media"
    return "alta"


def evaluate(i: VerdictInput, cfg: VerdictConfig = VERDICT) -> dict:
    conf = confidence(i.history_days, cfg)
    sale_soon = i.days_to_next_sale is not None and i.days_to_next_sale <= cfg.sale_window_days
    metrics = {
        "price_now": i.price_now, "min_ever": i.min_ever, "avg_all": i.avg_all, "avg_90d": i.avg_90d,
        "discount_pct": i.discount_pct, "days_to_next_sale": i.days_to_next_sale, "sale_name": i.sale_name,
        "history_days": i.history_days,
    }

    def out(v: str, reasons: list[str]) -> dict:
        return {"verdict": v, "confidence": conf, "reasons": reasons, "metrics": metrics}

    if i.price_now is None or i.min_ever is None or i.history_days < cfg.min_history_days:
        return out("INSUFICIENTE", [
            f"Histórico de apenas {i.history_days} dia(s): são necessários ao menos {cfg.min_history_days} "
            "para opinar sem inventar."])

    # A — no menor preço (ou muito perto)
    if i.price_now <= _lim(cfg.near_min_factor, i.min_ever):
        return out("COMPRAR_AGORA", [
            f"{brl(i.price_now)} está no menor preço histórico ou muito perto (mínimo {brl(i.min_ever)})."])

    above_min = (i.price_now / i.min_ever - 1) * 100 if i.min_ever else 0.0

    # B — grande liquidação chegando e preço bem acima do mínimo
    if sale_soon and i.price_now > _lim(cfg.wait_sale_min_factor, i.min_ever):
        when = i.sale_date.strftime("%d/%m/%Y") if i.sale_date else "em breve"
        starts = "está em andamento" if i.days_to_next_sale == 0 else f"começa em {i.days_to_next_sale} dia(s), {when}"
        return out("ESPERAR", [
            f"{i.sale_name} {starts} (datas aproximadas: verificar calendário oficial).",
            f"{brl(i.price_now)} é {above_min:.0f}% acima do menor preço, {brl(i.min_ever)}."])

    # C — acima da média recente, desconto baixo, sem liquidação próxima
    if (i.avg_90d is not None and i.price_now >= _lim(cfg.above_avg90_factor, i.avg_90d)
            and (i.discount_pct or 0) < cfg.low_discount_pct and not sale_soon):
        return out("ESPERAR", [
            f"{brl(i.price_now)} está acima da média recente (90 dias: {brl(i.avg_90d)}), "
            f"com desconto de apenas {(i.discount_pct or 0):.0f}% e sem grande liquidação nos próximos "
            f"{cfg.sale_window_days} dias."])

    # D — sem sinal forte
    reasons = [f"{brl(i.price_now)} é {above_min:.0f}% acima do menor preço ({brl(i.min_ever)}); sem sinal forte para comprar ou esperar."]
    if i.avg_90d is not None:
        reasons.append(f"Média dos últimos 90 dias: {brl(i.avg_90d)}.")
    return out("NEUTRO", reasons)

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntermarketInput:
    """Русский комментарий: нормализованные импульсы по рыночным кластерам."""

    br_score: float = 0.0
    ng_score: float = 0.0
    gold_score: float = 0.0
    silver_score: float = 0.0
    usdrub_score: float = 0.0
    cny_score: float = 0.0


@dataclass(frozen=True)
class IntermarketRegime:
    """Русский комментарий: итоговый межрыночный режим."""

    br_score: float
    ng_score: float
    gold_score: float
    silver_score: float
    usdrub_score: float
    cny_score: float
    commodity_score: float
    fx_stress_score: float
    risk_mode: str
    commodity_mode: str
    confidence: float
    reason: str


def clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def classify_intermarket_regime(data: IntermarketInput) -> IntermarketRegime:
    """
    Русский комментарий:
    v1-классификатор межрыночного режима.

    Интерпретация:
    - commodity_score > 0: сырьевой импульс вверх;
    - fx_stress_score > 0: рублевый/валютный стресс;
    - risk_mode: risk_on / risk_off / mixed / neutral;
    - commodity_mode: expansion / metals_bid / energy_bid / compression.
    """
    br = clamp(data.br_score)
    ng = clamp(data.ng_score)
    gold = clamp(data.gold_score)
    silver = clamp(data.silver_score)
    usd = clamp(data.usdrub_score)
    cny = clamp(data.cny_score)

    commodity_score = clamp((br + ng + gold + silver) / 4.0)
    fx_stress_score = clamp((usd + cny) / 2.0)

    if fx_stress_score > 0.25 and gold > 0.15:
        risk_mode = "RISK_OFF"
    elif commodity_score > 0.20 and fx_stress_score < 0.20:
        risk_mode = "RISK_ON_COMMODITY"
    elif abs(commodity_score) < 0.10 and abs(fx_stress_score) < 0.10:
        risk_mode = "NEUTRAL"
    else:
        risk_mode = "MIXED"

    energy_score = (br + ng) / 2.0
    metals_score = (gold + silver) / 2.0

    if commodity_score > 0.25:
        commodity_mode = "COMMODITY_EXPANSION"
    elif metals_score > 0.20 and energy_score <= 0.10:
        commodity_mode = "METALS_BID"
    elif energy_score > 0.20 and metals_score <= 0.10:
        commodity_mode = "ENERGY_BID"
    elif abs(commodity_score) < 0.10:
        commodity_mode = "LOW_IMPULSE"
    else:
        commodity_mode = "MIXED_COMMODITY"

    confidence = clamp(
        (
            abs(commodity_score)
            + abs(fx_stress_score)
            + abs(energy_score)
            + abs(metals_score)
        )
        / 4.0,
        0.0,
        1.0,
    )

    reason = (
        f"commodity={commodity_score:.6f};"
        f"fx_stress={fx_stress_score:.6f};"
        f"energy={energy_score:.6f};"
        f"metals={metals_score:.6f}"
    )

    return IntermarketRegime(
        br_score=br,
        ng_score=ng,
        gold_score=gold,
        silver_score=silver,
        usdrub_score=usd,
        cny_score=cny,
        commodity_score=commodity_score,
        fx_stress_score=fx_stress_score,
        risk_mode=risk_mode,
        commodity_mode=commodity_mode,
        confidence=confidence,
        reason=reason,
    )

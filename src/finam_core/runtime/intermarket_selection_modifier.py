from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntermarketSelectionModifier:
    score_multiplier: float
    confidence_delta: float
    recommendation_suffix: str
    reason: str


def build_intermarket_modifier(
    *,
    strategy: str,
    root_symbol: str,
    risk_mode: str,
    commodity_mode: str,
    confidence: float,
    commodity_score: float,
    fx_stress_score: float,
) -> IntermarketSelectionModifier:
    """
    Русский комментарий:
    Мягкий intermarket modifier для Runtime Selection v2.
    Не разрешает и не запрещает сделки напрямую.
    Только корректирует score/confidence/recommendation.
    """

    strategy_u = strategy.upper()
    root_u = root_symbol.upper()
    risk_u = risk_mode.upper()
    commodity_u = commodity_mode.upper()

    score_multiplier = 1.0
    confidence_delta = 0.0
    suffix = "IM_NEUTRAL"
    reason = "intermarket_neutral"

    is_commodity_strategy = (
        root_u in {"BR", "NG", "GOLD", "SILVER"}
        or "BR_" in strategy_u
        or "NG_" in strategy_u
    )

    if is_commodity_strategy and commodity_u == "COMMODITY_EXPANSION":
        score_multiplier = 1.15
        confidence_delta = min(0.10, confidence * 0.50)
        suffix = "IM_COMMODITY_BOOST"
        reason = "commodity_expansion_supports_breakout"

    elif is_commodity_strategy and risk_u == "RISK_OFF" and root_u in {"BR", "NG"}:
        score_multiplier = 0.75
        confidence_delta = -min(0.15, confidence * 0.70)
        suffix = "IM_RISK_OFF_REDUCE"
        reason = "risk_off_reduces_energy_breakout_quality"

    elif is_commodity_strategy and commodity_u == "LOW_IMPULSE":
        score_multiplier = 0.90
        confidence_delta = -min(0.08, confidence * 0.50)
        suffix = "IM_LOW_IMPULSE_REDUCE"
        reason = "low_commodity_impulse_reduces_breakout_quality"

    elif root_u in {"GOLD", "SILVER"} and commodity_u == "METALS_BID":
        score_multiplier = 1.10
        confidence_delta = min(0.08, confidence * 0.40)
        suffix = "IM_METALS_BID"
        reason = "metals_bid_supports_metals_strategy"

    elif fx_stress_score > 0.35:
        score_multiplier = 0.85
        confidence_delta = -min(0.10, confidence * 0.50)
        suffix = "IM_FX_STRESS_REDUCE"
        reason = "fx_stress_reduces_aggressive_entries"

    return IntermarketSelectionModifier(
        score_multiplier=round(score_multiplier, 8),
        confidence_delta=round(confidence_delta, 8),
        recommendation_suffix=suffix,
        reason=reason,
    )

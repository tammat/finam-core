from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioHeatDecision:
    heat: float
    status: str
    risk_multiplier: float
    allow_new_entries: bool
    reason: str


def evaluate_portfolio_heat(
    *,
    total_heat: float,
    elevated_threshold: float = 0.70,
    high_threshold: float = 1.00,
    critical_threshold: float = 1.30,
) -> PortfolioHeatDecision:
    """
    Русский комментарий:
    Advisory-only оценка общей нагретости портфеля.

    Не меняет:
    - RiskStack;
    - execution;
    - заявки;
    - позиции.

    Только возвращает решение для runtime governance.
    """

    heat = float(total_heat)

    if heat >= critical_threshold:
        return PortfolioHeatDecision(
            heat=round(heat, 10),
            status="CRITICAL",
            risk_multiplier=0.0,
            allow_new_entries=False,
            reason="portfolio_heat_critical_block_new_entries",
        )

    if heat >= high_threshold:
        return PortfolioHeatDecision(
            heat=round(heat, 10),
            status="HIGH",
            risk_multiplier=0.5,
            allow_new_entries=True,
            reason="portfolio_heat_high_reduce_risk",
        )

    if heat >= elevated_threshold:
        return PortfolioHeatDecision(
            heat=round(heat, 10),
            status="ELEVATED",
            risk_multiplier=0.75,
            allow_new_entries=True,
            reason="portfolio_heat_elevated_soft_reduce",
        )

    return PortfolioHeatDecision(
        heat=round(heat, 10),
        status="NORMAL",
        risk_multiplier=1.0,
        allow_new_entries=True,
        reason="portfolio_heat_normal",
    )

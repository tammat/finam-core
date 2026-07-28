from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegimeStrategyDecisionV1:
    strategy_code: str
    allowed_side: str
    reason_code: str
    countertrend_allowed: bool = False
    minimum_cost_buffer: float = 1.5
    exit_policy_code: str = "DYNAMIC_EXIT_V1"
    max_holding_bars: int = 20

    def allows(self, side: str) -> bool:
        normalized = str(side or "").upper()
        return self.allowed_side == "BOTH" or normalized == self.allowed_side


def resolve_regime_strategy_v1(
    *,
    trend: str,
    data_ready: bool,
    stale: bool,
) -> RegimeStrategyDecisionV1 | None:
    """Маршрутизирует подтверждённый режим без искусственного fallback.

    Боковик исследуется возвратом к среднему. Подтверждённый тренд —
    пробоем волатильности только в направлении тренда.
    """
    if not data_ready or stale:
        return None

    normalized = str(trend or "").strip().lower()
    if normalized == "range":
        return RegimeStrategyDecisionV1(
            strategy_code="MEAN_REVERSION_EQUITY",
            allowed_side="BOTH",
            reason_code="RANGE_TO_MEAN_REVERSION",
        )
    if normalized == "trend_up":
        return RegimeStrategyDecisionV1(
            strategy_code="VOLATILITY_BREAKOUT_EQUITY",
            allowed_side="BUY",
            reason_code="UPTREND_TO_LONG_BREAKOUT",
        )
    if normalized == "trend_down":
        return RegimeStrategyDecisionV1(
            strategy_code="VOLATILITY_BREAKOUT_EQUITY",
            allowed_side="SELL",
            reason_code="DOWNTREND_TO_SHORT_BREAKOUT",
        )
    return None

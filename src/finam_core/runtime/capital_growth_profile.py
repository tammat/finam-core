from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CapitalGrowthProfileConfig:
    profile: str
    risk_a: float
    risk_b: float
    min_score_a: float
    min_score_b: float
    max_daily_loss_pct: float
    max_active_growth_trades: int
    reason: str


class CapitalGrowthProfile:
    """Русский комментарий: профиль риска для режима разгона капитала."""

    def load(self, profile: str) -> CapitalGrowthProfileConfig:
        p = str(profile or "growth").lower()

        if p == "conservative":
            return CapitalGrowthProfileConfig(
                profile="conservative",
                risk_a=0.006,
                risk_b=0.004,
                min_score_a=75,
                min_score_b=60,
                max_daily_loss_pct=0.015,
                max_active_growth_trades=2,
                reason="консервативный разгон",
            )

        if p == "aggressive":
            return CapitalGrowthProfileConfig(
                profile="aggressive",
                risk_a=0.015,
                risk_b=0.000,
                min_score_a=80,
                min_score_b=999,
                max_daily_loss_pct=0.025,
                max_active_growth_trades=2,
                reason="агрессивный режим: только A-grade",
            )

        return CapitalGrowthProfileConfig(
            profile="growth",
            risk_a=0.012,
            risk_b=0.008,
            min_score_a=75,
            min_score_b=60,
            max_daily_loss_pct=0.020,
            max_active_growth_trades=3,
            reason="базовый управляемый разгон",
        )

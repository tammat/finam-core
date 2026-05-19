from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DailyLossGuardDecision:
    allowed: bool
    daily_pnl: float
    daily_loss_pct: float
    limit_pct: float
    reason: str


class CapitalGrowthDailyLossGuard:
    """Русский комментарий: блокирует режим разгона при превышении дневной просадки."""

    def check(
        self,
        *,
        equity: float,
        daily_pnl: float,
        max_daily_loss_pct: float,
    ) -> DailyLossGuardDecision:
        if equity <= 0:
            return DailyLossGuardDecision(False, daily_pnl, 0.0, max_daily_loss_pct, "equity<=0")

        daily_loss_pct = abs(min(daily_pnl, 0.0)) / equity

        if daily_loss_pct >= max_daily_loss_pct:
            return DailyLossGuardDecision(
                allowed=False,
                daily_pnl=round(daily_pnl, 2),
                daily_loss_pct=round(daily_loss_pct, 4),
                limit_pct=max_daily_loss_pct,
                reason=(
                    f"daily_loss_pct={daily_loss_pct:.4f};"
                    f"limit={max_daily_loss_pct:.4f}"
                ),
            )

        return DailyLossGuardDecision(
            allowed=True,
            daily_pnl=round(daily_pnl, 2),
            daily_loss_pct=round(daily_loss_pct, 4),
            limit_pct=max_daily_loss_pct,
            reason="daily_loss_within_limit",
        )

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CapitalGrowthGovernorDecision:
    allowed: bool
    active_growth_trades: int
    max_active_growth_trades: int
    reason: str


class CapitalGrowthPortfolioGovernor:
    """Русский комментарий: ограничивает количество активных сделок режима разгона."""

    def check(
        self,
        *,
        active_growth_trades: int,
        max_active_growth_trades: int,
    ) -> CapitalGrowthGovernorDecision:
        if max_active_growth_trades <= 0:
            return CapitalGrowthGovernorDecision(
                allowed=False,
                active_growth_trades=active_growth_trades,
                max_active_growth_trades=max_active_growth_trades,
                reason="max_active_growth_trades<=0",
            )

        if active_growth_trades >= max_active_growth_trades:
            return CapitalGrowthGovernorDecision(
                allowed=False,
                active_growth_trades=active_growth_trades,
                max_active_growth_trades=max_active_growth_trades,
                reason=(
                    f"active_growth_trades={active_growth_trades};"
                    f"limit={max_active_growth_trades}"
                ),
            )

        return CapitalGrowthGovernorDecision(
            allowed=True,
            active_growth_trades=active_growth_trades,
            max_active_growth_trades=max_active_growth_trades,
            reason="active_growth_trades_within_limit",
        )

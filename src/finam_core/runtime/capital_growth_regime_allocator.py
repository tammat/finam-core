from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CapitalGrowthRegimeDecision:
    profile: str
    allowed: bool
    reason: str


class CapitalGrowthRegimeAllocator:
    """Русский комментарий: динамически выбирает профиль разгона."""

    def decide(
        self,
        *,
        runtime_regime: str,
        portfolio_drawdown_pct: float,
        runtime_winrate: float,
        runtime_stress_level: str,
        market_breadth: float,
    ) -> CapitalGrowthRegimeDecision:

        regime = str(runtime_regime or "").lower()
        stress = str(runtime_stress_level or "").upper()

        # HARD DEFENSE
        if portfolio_drawdown_pct >= 0.08:
            return CapitalGrowthRegimeDecision(
                profile="conservative",
                allowed=True,
                reason="drawdown>=8%",
            )

        if stress in {"HIGH", "CRITICAL"}:
            return CapitalGrowthRegimeDecision(
                profile="conservative",
                allowed=True,
                reason=f"runtime_stress={stress}",
            )

        # AGGRESSIVE EXPANSION
        if (
            regime in {"trend_up_high_vol", "trend"}
            and runtime_winrate >= 0.58
            and market_breadth >= 0.60
            and portfolio_drawdown_pct <= 0.03
        ):
            return CapitalGrowthRegimeDecision(
                profile="aggressive",
                allowed=True,
                reason=(
                    f"trend={regime};"
                    f"winrate={runtime_winrate:.2f};"
                    f"breadth={market_breadth:.2f}"
                ),
            )

        # NORMAL GROWTH
        return CapitalGrowthRegimeDecision(
            profile="growth",
            allowed=True,
            reason=(
                f"default_growth;"
                f"regime={regime};"
                f"winrate={runtime_winrate:.2f}"
            ),
        )

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AutonomousPortfolioBrainDecision:
    portfolio_phase: str
    growth_profile: str
    max_risk_per_trade: float
    max_active_trades: int
    alert_aggressiveness: str
    capital_pressure: float
    allowed: bool
    reason: str


class AutonomousPortfolioBrain:
    """Русский комментарий: автономный управляющий слой всего портфеля."""

    def decide(
        self,
        *,
        equity: float,
        drawdown_pct: float,
        runtime_winrate: float,
        market_breadth: float,
        runtime_stress: str,
        open_positions: int,
        daily_pnl_pct: float,
        regime: str,
    ) -> AutonomousPortfolioBrainDecision:

        stress = str(runtime_stress or "").upper()
        regime = str(regime or "").lower()

        # CAPITAL PRESERVATION

        if (
            drawdown_pct >= 0.10
            or stress == "CRITICAL"
            or daily_pnl_pct <= -0.04
        ):
            return AutonomousPortfolioBrainDecision(
                portfolio_phase="CAPITAL_PRESERVATION",
                growth_profile="conservative",
                max_risk_per_trade=0.003,
                max_active_trades=1,
                alert_aggressiveness="LOW",
                capital_pressure=0.25,
                allowed=True,
                reason="capital_preservation_mode",
            )

        # RECOVERY

        if (
            drawdown_pct >= 0.06
            or daily_pnl_pct <= -0.025
        ):
            return AutonomousPortfolioBrainDecision(
                portfolio_phase="RECOVERY",
                growth_profile="conservative",
                max_risk_per_trade=0.005,
                max_active_trades=2,
                alert_aggressiveness="LOW",
                capital_pressure=0.50,
                allowed=True,
                reason="recovery_phase",
            )

        # DEFENSIVE

        if (
            stress == "HIGH"
            or market_breadth <= 0.35
            or runtime_winrate <= 0.45
        ):
            return AutonomousPortfolioBrainDecision(
                portfolio_phase="DEFENSIVE",
                growth_profile="growth",
                max_risk_per_trade=0.007,
                max_active_trades=3,
                alert_aggressiveness="MEDIUM",
                capital_pressure=0.75,
                allowed=True,
                reason="defensive_phase",
            )

        # OFFENSIVE EXPANSION

        if (
            regime in {"trend", "trend_up_high_vol"}
            and market_breadth >= 0.65
            and runtime_winrate >= 0.58
            and drawdown_pct <= 0.03
            and open_positions <= 4
        ):
            return AutonomousPortfolioBrainDecision(
                portfolio_phase="OFFENSIVE",
                growth_profile="aggressive",
                max_risk_per_trade=0.015,
                max_active_trades=6,
                alert_aggressiveness="HIGH",
                capital_pressure=1.75,
                allowed=True,
                reason="offensive_expansion_phase",
            )

        # BALANCED

        return AutonomousPortfolioBrainDecision(
            portfolio_phase="BALANCED",
            growth_profile="growth",
            max_risk_per_trade=0.010,
            max_active_trades=4,
            alert_aggressiveness="MEDIUM",
            capital_pressure=1.00,
            allowed=True,
            reason="balanced_phase",
        )

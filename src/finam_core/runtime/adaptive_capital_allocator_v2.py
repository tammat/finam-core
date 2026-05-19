from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdaptiveCapitalAllocationDecision:
    capital_multiplier: float
    allocation_pct: float
    allowed: bool
    reason: str


class AdaptiveCapitalAllocatorV2:
    """Русский комментарий: динамически регулирует капитал под setup."""

    def decide(
        self,
        *,
        trade_quality_score: float,
        expected_value: float,
        probability_tp: float,
        probability_sl: float,
        market_breadth: float,
        runtime_stress_level: str,
        portfolio_drawdown_pct: float,
        correlation_pressure: float,
        runtime_regime: str,
    ) -> AdaptiveCapitalAllocationDecision:

        multiplier = 1.0
        reasons: list[str] = []

        # POSITIVE FACTORS

        if trade_quality_score >= 85:
            multiplier += 0.30
            reasons.append("score>=85")

        elif trade_quality_score >= 75:
            multiplier += 0.15
            reasons.append("score>=75")

        if expected_value >= 2.5:
            multiplier += 0.20
            reasons.append("ev>=2.5")

        elif expected_value >= 1.5:
            multiplier += 0.10
            reasons.append("ev>=1.5")

        if probability_tp > probability_sl:
            edge = probability_tp - probability_sl

            if edge >= 0.25:
                multiplier += 0.20
                reasons.append("strong_probability_edge")

            elif edge >= 0.10:
                multiplier += 0.10
                reasons.append("probability_edge")

        if market_breadth >= 0.70:
            multiplier += 0.20
            reasons.append("breadth>=0.70")

        elif market_breadth >= 0.55:
            multiplier += 0.10
            reasons.append("breadth>=0.55")

        if runtime_regime in {"trend", "trend_up_high_vol"}:
            multiplier += 0.15
            reasons.append(f"trend_regime={runtime_regime}")

        # NEGATIVE FACTORS

        stress = str(runtime_stress_level or "").upper()

        if stress == "HIGH":
            multiplier -= 0.35
            reasons.append("stress=HIGH")

        elif stress == "CRITICAL":
            multiplier -= 0.60
            reasons.append("stress=CRITICAL")

        if portfolio_drawdown_pct >= 0.08:
            multiplier -= 0.40
            reasons.append("drawdown>=8%")

        elif portfolio_drawdown_pct >= 0.05:
            multiplier -= 0.20
            reasons.append("drawdown>=5%")

        if correlation_pressure >= 0.70:
            multiplier -= 0.25
            reasons.append("correlation>=0.70")

        elif correlation_pressure >= 0.50:
            multiplier -= 0.10
            reasons.append("correlation>=0.50")

        # HARD FLOOR / CEILING

        multiplier = max(0.25, min(multiplier, 2.0))

        allocation_pct = multiplier * 100.0

        if multiplier <= 0.30:
            return AdaptiveCapitalAllocationDecision(
                capital_multiplier=multiplier,
                allocation_pct=allocation_pct,
                allowed=False,
                reason="capital_allocation_blocked;" + ";".join(reasons),
            )

        return AdaptiveCapitalAllocationDecision(
            capital_multiplier=multiplier,
            allocation_pct=allocation_pct,
            allowed=True,
            reason=";".join(reasons),
        )

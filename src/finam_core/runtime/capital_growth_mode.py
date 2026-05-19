from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CapitalGrowthDecision:
    allowed: bool
    risk_pct: float
    mode: str
    reason: str


class CapitalGrowthMode:
    """Русский комментарий: режим управляемого разгона капитала."""

    def decide(
        self,
        *,
        trade_quality_grade: str,
        trade_quality_score: float,
        expected_value: float,
        probability_tp: float,
        probability_sl: float,
        risk_reward: float,
        portfolio_heat: float,
        runtime_severity: str,
    ) -> CapitalGrowthDecision:

        grade = str(trade_quality_grade or "D").upper()
        severity = str(runtime_severity or "INFO").upper()

        if severity in {"WARNING", "CRITICAL"}:
            return CapitalGrowthDecision(
                allowed=False,
                risk_pct=0.0,
                mode="BLOCK",
                reason=f"runtime_severity={severity}",
            )

        if portfolio_heat >= 0.70:
            return CapitalGrowthDecision(
                allowed=False,
                risk_pct=0.0,
                mode="BLOCK",
                reason=f"portfolio_heat={portfolio_heat:.2f}",
            )

        if expected_value <= 0:
            return CapitalGrowthDecision(
                allowed=False,
                risk_pct=0.0,
                mode="BLOCK",
                reason="expected_value<=0",
            )

        if probability_tp <= probability_sl:
            return CapitalGrowthDecision(
                allowed=False,
                risk_pct=0.0,
                mode="BLOCK",
                reason="probability_edge<=0",
            )

        if risk_reward < 1.8:
            return CapitalGrowthDecision(
                allowed=False,
                risk_pct=0.0,
                mode="BLOCK",
                reason="risk_reward<1.8",
            )

        if grade == "A" and trade_quality_score >= 75:
            return CapitalGrowthDecision(
                allowed=True,
                risk_pct=0.012,
                mode="AGGRESSIVE_CONTROLLED",
                reason="A-grade setup; risk=1.2%",
            )

        if grade == "B" and trade_quality_score >= 60:
            return CapitalGrowthDecision(
                allowed=True,
                risk_pct=0.008,
                mode="NORMAL_GROWTH",
                reason="B-grade setup; risk=0.8%",
            )

        return CapitalGrowthDecision(
            allowed=False,
            risk_pct=0.0,
            mode="WATCH_ONLY",
            reason=f"grade={grade};score={trade_quality_score:.2f}",
        )

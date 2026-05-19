from __future__ import annotations

from dataclasses import dataclass

from finam_core.runtime.capital_growth_profile import CapitalGrowthProfile


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
        daily_loss_allowed: bool = True,
        daily_loss_reason: str = "",
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

        if not daily_loss_allowed:
            return CapitalGrowthDecision(
                allowed=False,
                risk_pct=0.0,
                mode="BLOCK",
                reason=f"daily_loss_guard:{daily_loss_reason}",
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

        import os

        profile = CapitalGrowthProfile().load(
            os.getenv("CAPITAL_GROWTH_PROFILE", "growth")
        )

        if grade == "A" and trade_quality_score >= profile.min_score_a:
            return CapitalGrowthDecision(
                allowed=True,
                risk_pct=profile.risk_a,
                mode=f"{profile.profile.upper()}_A_GRADE",
                reason=f"{profile.reason}; A-grade risk={profile.risk_a * 100:.2f}%",
            )

        if grade == "B" and trade_quality_score >= profile.min_score_b and profile.risk_b > 0:
            return CapitalGrowthDecision(
                allowed=True,
                risk_pct=profile.risk_b,
                mode=f"{profile.profile.upper()}_B_GRADE",
                reason=f"{profile.reason}; B-grade risk={profile.risk_b * 100:.2f}%",
            )

        return CapitalGrowthDecision(
            allowed=False,
            risk_pct=0.0,
            mode="WATCH_ONLY",
            reason=f"grade={grade};score={trade_quality_score:.2f}",
        )

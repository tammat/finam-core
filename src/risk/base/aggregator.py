from __future__ import annotations

from dataclasses import dataclass

from risk.base.result import RiskRuleResult


@dataclass(slots=True)
class RiskAggregateResult:
    risk_score: float
    position_risk_score: float
    exposure_risk_score: float
    daily_loss_risk_score: float
    correlation_risk_score: float
    kill_switch_score: float
    decision_code: str
    recommendation_code: str


class RiskAggregator:

    def aggregate(self, results: list[RiskRuleResult]) -> RiskAggregateResult:

        if not results:
            return RiskAggregateResult(
                risk_score=0.0,
                position_risk_score=0.0,
                exposure_risk_score=0.0,
                daily_loss_risk_score=0.0,
                correlation_risk_score=0.0,
                kill_switch_score=0.0,
                decision_code="RISK_BLOCK",
                recommendation_code="WAIT_RISK_REVIEW",
            )

        risk_score = sum(r.risk_score for r in results) / len(results)

        if risk_score >= 1.0:
            decision = "RISK_ALLOW"
            recommendation = "READY_FOR_TRADING"
        elif risk_score >= 0.50:
            decision = "RISK_OBSERVE"
            recommendation = "WAIT_RISK_REVIEW"
        else:
            decision = "RISK_BLOCK"
            recommendation = "BLOCK_RISK"

        return RiskAggregateResult(
            risk_score=risk_score,
            position_risk_score=risk_score,
            exposure_risk_score=risk_score,
            daily_loss_risk_score=risk_score,
            correlation_risk_score=risk_score,
            kill_switch_score=risk_score,
            decision_code=decision,
            recommendation_code=recommendation,
        )

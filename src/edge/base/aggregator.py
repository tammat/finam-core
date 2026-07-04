from __future__ import annotations

from dataclasses import dataclass

from edge.base.result import EdgeRuleResult


@dataclass(slots=True)
class EdgeAggregateResult:
    edge_score: float
    validation_score: float
    governance_score: float
    decision_code: str
    recommendation_code: str


class EdgeAggregator:

    def aggregate(self, results: list[EdgeRuleResult]) -> EdgeAggregateResult:

        if not results:
            return EdgeAggregateResult(
                edge_score=0.0,
                validation_score=0.0,
                governance_score=0.0,
                decision_code="WAIT_RESEARCH",
                recommendation_code="WAIT_RESEARCH",
            )

        edge_score = sum(r.score for r in results) / len(results)

        return EdgeAggregateResult(
            edge_score=edge_score,
            validation_score=0.0,
            governance_score=0.0,
            decision_code="WAIT_RESEARCH",
            recommendation_code="WAIT_RESEARCH",
        )

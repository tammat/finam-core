from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from marketcore.recommendation.models import RecommendationContext


@dataclass(frozen=True)
class RecommendationRule:
    rule_code: str
    recommendation_code: str
    priority: int
    conditions: list[dict[str, Any]]


@dataclass(frozen=True)
class EvaluatedRecommendation:
    symbol: str
    timeframe: str
    recommendation_code: str
    recommendation_confidence: Decimal
    rule_code: str
    reasons: list[dict[str, Any]]
    evidence: dict[str, Any]


class RecommendationEvaluator:
    def evaluate(
        self,
        context: RecommendationContext,
        rules: list[RecommendationRule],
        parameters: dict[str, object],
    ) -> EvaluatedRecommendation:
        metrics = self._metrics(context)

        for rule in sorted(rules, key=lambda r: r.priority):
            reasons: list[dict[str, Any]] = []
            matched = True

            for condition in rule.conditions:
                metric_code = str(condition["metric_code"])
                operator_code = str(condition["operator_code"])
                parameter_code = str(condition["parameter_code"])

                metric_value = metrics.get(metric_code)
                parameter_value = parameters.get(parameter_code)

                if metric_value is None or parameter_value is None:
                    matched = False
                    break

                if not self._compare(
                    Decimal(str(metric_value)),
                    operator_code,
                    Decimal(str(parameter_value)),
                ):
                    matched = False
                    break

                reasons.append(
                    {
                        "reason_code": f"reason.{metric_code.lower()}.{operator_code.lower()}",
                        "reason_value": str(metric_value),
                        "confidence": str(self._confidence_from_metric(metric_value)),
                        "parameter_code": parameter_code,
                    }
                )

            if matched and reasons:
                confidence = self._aggregate_confidence(context, reasons)
                return EvaluatedRecommendation(
                    symbol=context.symbol,
                    timeframe=context.timeframe,
                    recommendation_code=rule.recommendation_code,
                    recommendation_confidence=confidence,
                    rule_code=rule.rule_code,
                    reasons=reasons,
                    evidence={
                        "market_context_id": context.market_context_id,
                        "edge_context_id": context.edge_context_id,
                        "knowledge_coverage": str(context.knowledge_coverage),
                        "relationships": len(context.relationships),
                    },
                )

        return EvaluatedRecommendation(
            symbol=context.symbol,
            timeframe=context.timeframe,
            recommendation_code="INSUFFICIENT_DATA",
            recommendation_confidence=Decimal("0"),
            rule_code="NO_MATCHED_RULE",
            reasons=[
                {
                    "reason_code": "reason.insufficient_data",
                    "reason_value": "NO_MATCHED_RULE",
                    "confidence": "0",
                }
            ],
            evidence={
                "market_context_id": context.market_context_id,
                "edge_context_id": context.edge_context_id,
                "knowledge_coverage": str(context.knowledge_coverage),
                "relationships": len(context.relationships),
            },
        )

    def _metrics(self, context: RecommendationContext) -> dict[str, Decimal]:
        return {
            "EDGE_SCORE": context.edge_score,
            "KNOWLEDGE_COVERAGE": context.knowledge_coverage * Decimal("100"),
            "RELATIONSHIP_COUNT": Decimal(len(context.relationships)),
        }

    def _compare(self, left: Decimal, operator_code: str, right: Decimal) -> bool:
        if operator_code == "GE":
            return left >= right
        if operator_code == "GT":
            return left > right
        if operator_code == "LE":
            return left <= right
        if operator_code == "LT":
            return left < right
        if operator_code == "EQ":
            return left == right
        if operator_code == "NE":
            return left != right
        return False

    def _confidence_from_metric(self, value: Any) -> Decimal:
        numeric = Decimal(str(value))
        if numeric < 0:
            return Decimal("0")
        if numeric > 100:
            return Decimal("1")
        return (numeric / Decimal("100")).quantize(Decimal("0.0001"))

    def _aggregate_confidence(
        self,
        context: RecommendationContext,
        reasons: list[dict[str, Any]],
    ) -> Decimal:
        reason_values = [Decimal(str(r["confidence"])) for r in reasons]
        base = sum(reason_values) / Decimal(len(reason_values))
        coverage = context.knowledge_coverage
        confidence = (base + coverage) / Decimal("2")
        if confidence > 1:
            return Decimal("1")
        if confidence < 0:
            return Decimal("0")
        return confidence.quantize(Decimal("0.0001"))

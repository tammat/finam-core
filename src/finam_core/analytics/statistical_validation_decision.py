from __future__ import annotations

from dataclasses import dataclass

from finam_core.analytics.statistical_validation_engine import StatisticalValidationResult


@dataclass(frozen=True)
class StatisticalValidationDecision:
    decision: str
    reason: str
    confidence: float


class StatisticalValidationDecisionEngine:
    """Русский комментарий: переводит bootstrap-статистику в управленческое решение."""

    def decide(self, result: StatisticalValidationResult) -> StatisticalValidationDecision:
        if result.trades < 30:
            return StatisticalValidationDecision(
                decision="INSUFFICIENT_DATA",
                reason="trades_below_minimum_30",
                confidence=result.probability_positive_expectancy,
            )

        if result.expectancy_ci_low <= 0 <= result.expectancy_ci_high:
            if result.probability_positive_expectancy < 0.70:
                return StatisticalValidationDecision(
                    decision="REJECT",
                    reason="ci_crosses_zero_and_low_positive_probability",
                    confidence=result.probability_positive_expectancy,
                )

            return StatisticalValidationDecision(
                decision="WATCH",
                reason="ci_crosses_zero",
                confidence=result.probability_positive_expectancy,
            )

        if result.probability_positive_expectancy >= 0.95 and result.expectancy_ci_low > 0:
            return StatisticalValidationDecision(
                decision="ACCEPT_STRONG",
                reason="positive_expectancy_high_confidence",
                confidence=result.probability_positive_expectancy,
            )

        if result.probability_positive_expectancy >= 0.85 and result.expectancy > 0:
            return StatisticalValidationDecision(
                decision="ACCEPT_WEAK",
                reason="positive_expectancy_moderate_confidence",
                confidence=result.probability_positive_expectancy,
            )

        return StatisticalValidationDecision(
            decision="WATCH",
            reason="default_watch",
            confidence=result.probability_positive_expectancy,
        )

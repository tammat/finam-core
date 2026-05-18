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
                decision="НЕДОСТАТОЧНО_ДАННЫХ",
                reason="недостаточно_сделок",
                confidence=result.probability_positive_expectancy,
            )

        if result.expectancy_ci_low <= 0 <= result.expectancy_ci_high:
            if result.probability_positive_expectancy < 0.70:
                return StatisticalValidationDecision(
                    decision="ОТКЛОНИТЬ",
                    reason="интервал_пересекает_ноль_низкая_вероятность",
                    confidence=result.probability_positive_expectancy,
                )

            return StatisticalValidationDecision(
                decision="НАБЛЮДЕНИЕ",
                reason="доверительный_интервал_пересекает_ноль",
                confidence=result.probability_positive_expectancy,
            )

        if result.probability_positive_expectancy >= 0.95 and result.expectancy_ci_low > 0:
            return StatisticalValidationDecision(
                decision="ПРИНЯТЬ",
                reason="положительное_матожидание_высокая_уверенность",
                confidence=result.probability_positive_expectancy,
            )

        if result.probability_positive_expectancy >= 0.85 and result.expectancy > 0:
            return StatisticalValidationDecision(
                decision="ПРИНЯТЬ_УСЛОВНО",
                reason="положительное_матожидание_умеренная_уверенность",
                confidence=result.probability_positive_expectancy,
            )

        return StatisticalValidationDecision(
            decision="НАБЛЮДЕНИЕ",
            reason="требуется_наблюдение",
            confidence=result.probability_positive_expectancy,
        )

from typing import Any

from .result import ClassifierResult


class ClassifierPipeline:
    # Минимальный rule-based pipeline V1.
    # Не использует PnL, сделки, Runtime и Execution.

    def run(self, features: dict[str, Any]) -> tuple[ClassifierResult, ...]:
        results: list[ClassifierResult] = []

        trend = str(features.get("trend", "UNKNOWN"))
        volatility = str(features.get("volatility", "UNKNOWN"))
        session = str(features.get("session", "UNKNOWN"))

        results.append(
            ClassifierResult(
                group="TREND",
                state=trend,
                confidence=0.50 if trend == "UNKNOWN" else 0.80,
                explanation_ru=f"TREND определен из входного признака trend={trend}",
                classifier_version="TrendClassifierV1",
            )
        )
        results.append(
            ClassifierResult(
                group="VOLATILITY",
                state=volatility,
                confidence=0.50 if volatility == "UNKNOWN" else 0.80,
                explanation_ru=f"VOLATILITY определена из входного признака volatility={volatility}",
                classifier_version="VolatilityClassifierV1",
            )
        )
        results.append(
            ClassifierResult(
                group="SESSION_BUCKET",
                state=session,
                confidence=0.50 if session == "UNKNOWN" else 0.80,
                explanation_ru=f"SESSION_BUCKET определена из входного признака session={session}",
                classifier_version="SessionClassifierV1",
            )
        )

        return tuple(results)

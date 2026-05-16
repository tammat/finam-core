from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SignalConfidenceDecision:
    confidence: float
    institutional_confirmed: bool
    action: str
    reason: str


class SignalConfidenceEngine:
    """Русский комментарий: объединяет стратегический сигнал и smart-money подтверждение."""

    def evaluate(
        self,
        base_score: float,
        smart_money_score: float = 0.0,
        regime_alignment: float = 0.5,
        spread_quality: float = 1.0,
        volatility_quality: float = 0.5,
    ) -> SignalConfidenceDecision:
        base_score = self._clip(base_score)
        smart_money_score = self._clip(smart_money_score)
        regime_alignment = self._clip(regime_alignment)
        spread_quality = self._clip(spread_quality)
        volatility_quality = self._clip(volatility_quality)

        confidence = round(
            base_score * 0.35
            + smart_money_score * 0.25
            + regime_alignment * 0.20
            + spread_quality * 0.10
            + volatility_quality * 0.10,
            6,
        )

        institutional_confirmed = smart_money_score >= 0.70

        if confidence >= 0.70:
            action = "ACCEPT"
        elif confidence >= 0.55 and smart_money_score >= 0.45:
            action = "WATCH"
        else:
            action = "REJECT"

        reason = (
            f"confidence={confidence};"
            f"base_score={base_score};"
            f"smart_money_score={smart_money_score};"
            f"regime_alignment={regime_alignment};"
            f"spread_quality={spread_quality};"
            f"volatility_quality={volatility_quality};"
            f"institutional_confirmed={institutional_confirmed}"
        )

        return SignalConfidenceDecision(
            confidence=confidence,
            institutional_confirmed=institutional_confirmed,
            action=action,
            reason=reason,
        )

    @staticmethod
    def _clip(value: float) -> float:
        return max(0.0, min(float(value or 0.0), 1.0))

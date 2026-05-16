from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdaptivePositionDecision:
    base_qty: float
    final_qty: float
    multiplier: float
    confidence_multiplier: float
    institutional_multiplier: float
    volatility_multiplier: float
    heat_multiplier: float
    reason: str


class AdaptivePositionSizer:
    """Русский комментарий: адаптивно масштабирует размер позиции по качеству сигнала."""

    def __init__(
        self,
        min_multiplier: float = 0.25,
        max_multiplier: float = 1.50,
    ) -> None:
        self.min_multiplier = float(min_multiplier)
        self.max_multiplier = float(max_multiplier)

    def size(
        self,
        base_qty: float,
        confidence: float,
        institutional_flow_regime: str = "NORMAL_FLOW",
        institutional_flow_bias: str = "NEUTRAL",
        smart_money_score: float = 0.0,
        volatility_quality: float = 0.5,
        portfolio_heat: float = 0.0,
    ) -> AdaptivePositionDecision:
        base_qty = max(float(base_qty or 0.0), 0.0)
        confidence = self._clip(confidence)
        smart_money_score = self._clip(smart_money_score)
        volatility_quality = self._clip(volatility_quality)
        portfolio_heat = self._clip(portfolio_heat)

        confidence_multiplier = self._confidence_multiplier(confidence)
        institutional_multiplier = self._institutional_multiplier(
            institutional_flow_regime,
            institutional_flow_bias,
            smart_money_score,
        )
        volatility_multiplier = self._volatility_multiplier(volatility_quality)
        heat_multiplier = self._heat_multiplier(portfolio_heat)

        multiplier = (
            confidence_multiplier
            * institutional_multiplier
            * volatility_multiplier
            * heat_multiplier
        )

        multiplier = max(
            self.min_multiplier,
            min(multiplier, self.max_multiplier),
        )

        final_qty = round(base_qty * multiplier, 6)

        reason = (
            f"base_qty={base_qty};"
            f"final_qty={final_qty};"
            f"multiplier={round(multiplier, 6)};"
            f"confidence={confidence};"
            f"confidence_multiplier={round(confidence_multiplier, 6)};"
            f"institutional_flow_regime={institutional_flow_regime};"
            f"institutional_flow_bias={institutional_flow_bias};"
            f"institutional_multiplier={round(institutional_multiplier, 6)};"
            f"smart_money_score={smart_money_score};"
            f"volatility_quality={volatility_quality};"
            f"volatility_multiplier={round(volatility_multiplier, 6)};"
            f"portfolio_heat={portfolio_heat};"
            f"heat_multiplier={round(heat_multiplier, 6)}"
        )

        return AdaptivePositionDecision(
            base_qty=base_qty,
            final_qty=final_qty,
            multiplier=round(multiplier, 6),
            confidence_multiplier=round(confidence_multiplier, 6),
            institutional_multiplier=round(institutional_multiplier, 6),
            volatility_multiplier=round(volatility_multiplier, 6),
            heat_multiplier=round(heat_multiplier, 6),
            reason=reason,
        )

    def _confidence_multiplier(self, confidence: float) -> float:
        if confidence >= 0.85:
            return 1.30
        if confidence >= 0.70:
            return 1.15
        if confidence >= 0.55:
            return 1.00
        if confidence >= 0.45:
            return 0.75
        return 0.50

    def _institutional_multiplier(
        self,
        regime: str,
        bias: str,
        smart_money_score: float,
    ) -> float:
        regime = str(regime or "NORMAL_FLOW")
        bias = str(bias or "NEUTRAL")

        if regime == "TREND_INITIATION":
            return 1.35
        if regime == "ACCUMULATION":
            return 1.25
        if regime == "INSTITUTIONAL_PARTICIPATION":
            return 1.15
        if regime == "BREAKOUT_TRAP":
            return 0.50

        if smart_money_score >= 0.70:
            return 1.10

        return 1.00

    def _volatility_multiplier(self, volatility_quality: float) -> float:
        if volatility_quality >= 0.80:
            return 1.10
        if volatility_quality >= 0.45:
            return 1.00
        return 0.80

    def _heat_multiplier(self, portfolio_heat: float) -> float:
        if portfolio_heat >= 0.85:
            return 0.25
        if portfolio_heat >= 0.65:
            return 0.50
        if portfolio_heat >= 0.45:
            return 0.75
        return 1.00

    @staticmethod
    def _clip(value: float) -> float:
        return max(0.0, min(float(value or 0.0), 1.0))

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InstitutionalFlowRegime:
    symbol: str
    regime: str
    bias: str
    confidence: float
    reason: str


class InstitutionalFlowRegimeEngine:
    """Русский комментарий: интерпретирует smart-money признаки в режим крупного потока."""

    def classify(
        self,
        symbol: str,
        smart_money_score: float,
        rvol: float,
        absorption_score: float,
        sweep_reclaim_score: float,
        impulse_score: float,
        price_velocity: float = 0.0,
        range_pct: float = 0.0,
    ) -> InstitutionalFlowRegime:
        smart_money_score = self._clip(smart_money_score)
        rvol = max(float(rvol or 0.0), 0.0)
        absorption_score = self._clip(absorption_score)
        sweep_reclaim_score = self._clip(sweep_reclaim_score)
        impulse_score = self._clip(impulse_score)
        price_velocity = max(float(price_velocity or 0.0), 0.0)
        range_pct = max(float(range_pct or 0.0), 0.0)

        regime = "NORMAL_FLOW"
        bias = "NEUTRAL"
        confidence = smart_money_score

        if absorption_score >= 0.65 and rvol >= 2.0 and range_pct <= 0.006:
            regime = "ACCUMULATION"
            bias = "LONG_BIAS"
            confidence = max(confidence, absorption_score)

        elif sweep_reclaim_score >= 0.60 and rvol >= 1.5:
            regime = "BREAKOUT_TRAP"
            bias = "FADE_BIAS"
            confidence = max(confidence, sweep_reclaim_score)

        elif impulse_score >= 0.65 and smart_money_score >= 0.45 and price_velocity >= 0.003:
            regime = "TREND_INITIATION"
            bias = "MOMENTUM_BIAS"
            confidence = max(confidence, impulse_score)

        elif smart_money_score >= 0.70 and impulse_score >= 0.45:
            regime = "INSTITUTIONAL_PARTICIPATION"
            bias = "FOLLOW_FLOW"
            confidence = max(confidence, smart_money_score)

        reason = (
            f"regime={regime};"
            f"bias={bias};"
            f"smart_money_score={smart_money_score};"
            f"rvol={rvol};"
            f"absorption_score={absorption_score};"
            f"sweep_reclaim_score={sweep_reclaim_score};"
            f"impulse_score={impulse_score};"
            f"price_velocity={price_velocity};"
            f"range_pct={range_pct}"
        )

        return InstitutionalFlowRegime(
            symbol=symbol,
            regime=regime,
            bias=bias,
            confidence=round(confidence, 6),
            reason=reason,
        )

    @staticmethod
    def _clip(value: float) -> float:
        return max(0.0, min(float(value or 0.0), 1.0))

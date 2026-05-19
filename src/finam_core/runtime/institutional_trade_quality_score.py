from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TradeQualityScore:
    score: float
    grade: str
    reason: str


class InstitutionalTradeQualityScorer:
    """Русский комментарий: считает итоговое качество сделки для отбора лучших ALERT."""

    def score(
        self,
        *,
        probability_tp: float,
        probability_sl: float,
        expected_value_pct: float,
        risk_reward: float,
        signal_score: float,
        correlation_pressure: int,
        risk_multiplier: float,
    ) -> TradeQualityScore:
        raw = 0.0

        raw += max(probability_tp - probability_sl, 0.0) * 30.0
        raw += max(expected_value_pct, 0.0) * 8.0
        raw += min(risk_reward, 3.0) * 10.0
        raw += min(signal_score, 5.0) * 5.0
        raw += min(risk_multiplier, 1.5) * 10.0

        raw -= correlation_pressure * 8.0

        score = round(max(min(raw, 100.0), 0.0), 2)

        if score >= 75:
            grade = "A"
        elif score >= 60:
            grade = "B"
        elif score >= 45:
            grade = "C"
        else:
            grade = "D"

        return TradeQualityScore(
            score=score,
            grade=grade,
            reason=(
                f"p_edge={(probability_tp - probability_sl):.4f};"
                f"ev_pct={expected_value_pct:.4f};"
                f"rr={risk_reward:.2f};"
                f"signal_score={signal_score:.2f};"
                f"risk_multiplier={risk_multiplier:.2f};"
                f"correlation_pressure={correlation_pressure}"
            ),
        )

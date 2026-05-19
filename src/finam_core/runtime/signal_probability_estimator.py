from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SignalProbability:
    probability_tp: float
    probability_sl: float
    probability_expire: float
    sample_size: int


class SignalProbabilityEstimator:
    """Русский комментарий: оценивает вероятность TP/SL по истории lifecycle."""

    def estimate(
        self,
        *,
        tp_hits: int,
        sl_hits: int,
        expired: int,
    ) -> SignalProbability:
        total = tp_hits + sl_hits + expired

        if total <= 0:
            return SignalProbability(
                probability_tp=0.0,
                probability_sl=0.0,
                probability_expire=0.0,
                sample_size=0,
            )

        return SignalProbability(
            probability_tp=round(tp_hits / total, 4),
            probability_sl=round(sl_hits / total, 4),
            probability_expire=round(expired / total, 4),
            sample_size=total,
        )

from __future__ import annotations


def classify_ng_regime(
    *,
    atr_percent: float,
    ema_slope: float,
    compression_score: float,
) -> str:
    """
    Русский комментарий:
    Классификатор режимов газа.
    """

    if compression_score >= 0.8:
        return "COMPRESSION"

    if atr_percent >= 2.5:
        if ema_slope > 0:
            return "HIGH_VOL_TREND_UP"

        if ema_slope < 0:
            return "HIGH_VOL_TREND_DOWN"

        return "HIGH_VOL_RANGE"

    if atr_percent <= 1.0:
        return "LOW_VOL"

    if abs(ema_slope) < 0.05:
        return "RANGE"

    if ema_slope > 0:
        return "TREND_UP"

    return "TREND_DOWN"

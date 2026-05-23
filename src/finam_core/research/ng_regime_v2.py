from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NgRegimeFeaturesV2:
    atr_percent: float
    atr_expansion: float
    range_expansion: float
    ema_slope: float
    compression_score: float
    breakout_strength: float
    session_bucket: str


def classify_ng_regime_v2(f: NgRegimeFeaturesV2) -> str:
    """
    Русский комментарий:
    Commodity-aware regime classifier для NG.
    Газ классифицируется по расширению волатильности, направлению и сессии.
    """

    if f.breakout_strength >= 1.5 and f.atr_expansion >= 1.2:
        if f.ema_slope > 0:
            return "EXPANSION_TREND_UP"
        if f.ema_slope < 0:
            return "EXPANSION_TREND_DOWN"
        return "EXPANSION_RANGE"

    if f.session_bucket == "US_OPEN_WINDOW" and f.range_expansion >= 1.3:
        return "US_OPEN_IMPULSE"

    if f.compression_score >= 0.75 and f.range_expansion >= 1.2:
        return "SQUEEZE_BREAKOUT"

    if f.atr_percent >= 2.5:
        return "HIGH_VOL"

    if f.compression_score >= 0.8:
        return "COMPRESSION"

    if abs(f.ema_slope) >= 0.08:
        return "TREND_UP" if f.ema_slope > 0 else "TREND_DOWN"

    return "RANGE_LOW_VOL"

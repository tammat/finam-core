from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrCompressionWatchDecision:
    active: bool
    reason: str
    compression_ratio: float
    atr_pct: float
    threshold: float


class BrCompressionWatch:
    """Русский комментарий: watch-only режим сжатия Brent без разрешения сделки."""

    def __init__(self, activation_ratio: float = 0.65):
        self.activation_ratio = float(activation_ratio)

    def decide(self, *, atr_pct: float, threshold: float) -> BrCompressionWatchDecision:
        threshold_value = float(threshold or 0.0)
        atr_value = float(atr_pct or 0.0)

        if threshold_value <= 0:
            return BrCompressionWatchDecision(
                active=False,
                reason="invalid_threshold",
                compression_ratio=0.0,
                atr_pct=atr_value,
                threshold=threshold_value,
            )

        ratio = atr_value / threshold_value
        active = ratio <= self.activation_ratio
        reason = "compression_watch_active" if active else "compression_watch_inactive"

        return BrCompressionWatchDecision(
            active=active,
            reason=reason,
            compression_ratio=float(ratio),
            atr_pct=atr_value,
            threshold=threshold_value,
        )

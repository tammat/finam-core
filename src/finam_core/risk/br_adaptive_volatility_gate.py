from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrVolatilityGateDecision:
    allowed: bool
    reason: str
    atr_pct: float
    threshold: float
    mode: str


class BrAdaptiveVolatilityGate:
    """Русский комментарий: адаптивный volatility gate для Brent без изменения ядра."""

    def __init__(self, min_threshold: float = 0.0008, max_threshold: float = 0.0025):
        self.min_threshold = float(min_threshold)
        self.max_threshold = float(max_threshold)

    def decide(
        self,
        *,
        atr_pct: float,
        static_threshold: float,
        regime_volatility: str,
    ) -> BrVolatilityGateDecision:
        vol = str(regime_volatility or "normal").lower()

        if vol == "high":
            threshold = min(float(static_threshold), self.max_threshold)
            mode = "high_vol_static_cap"
        elif vol == "normal":
            threshold = max(float(static_threshold) * 0.60, self.min_threshold)
            mode = "normal_vol_adaptive"
        else:
            threshold = max(float(static_threshold) * 0.50, self.min_threshold)
            mode = "low_vol_adaptive"

        allowed = float(atr_pct or 0.0) >= threshold
        reason = "br_volatility_ok" if allowed else "br_volatility_too_low"

        return BrVolatilityGateDecision(
            allowed=allowed,
            reason=reason,
            atr_pct=float(atr_pct or 0.0),
            threshold=float(threshold),
            mode=mode,
        )

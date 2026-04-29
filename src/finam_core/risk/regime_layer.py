# src/finam_core/risk/regime_layer.py

from __future__ import annotations

import os
from collections import deque
from dataclasses import dataclass


@dataclass
class RegimeDecision:
    regime: str
    allowed: bool
    reason: str
    atr: float
    slope: float


class RegimeLayer:
    """
    Русский коммент: Regime Layer классифицирует рынок перед входом.
    Не отправляет заявки, только разрешает/запрещает сигнал.
    """

    def __init__(self):
        self.min_atr = float(os.getenv("REGIME_MIN_ATR", "0.03"))
        self.max_atr = float(os.getenv("REGIME_MAX_ATR", "0.80"))
        self.slope_window = int(os.getenv("REGIME_SLOPE_WINDOW", "5"))
        self.min_slope = float(os.getenv("REGIME_MIN_SLOPE", "0.0"))
        self.prices = deque(maxlen=max(self.slope_window, 2))

    def update(self, price) -> float:
        try:
            px = float(price)
        except Exception:
            return 0.0

        self.prices.append(px)

        if len(self.prices) < 2:
            return 0.0

        return self.prices[-1] - self.prices[0]

    def evaluate(self, atr: float | None, price=None) -> RegimeDecision:
        slope = self.update(price) if price is not None else 0.0

        try:
            atr_value = float(atr)
        except Exception:
            atr_value = 0.0

        if atr_value < self.min_atr:
            return RegimeDecision("low_volatility", False, "atr_below_min", atr_value, slope)

        if atr_value > self.max_atr:
            return RegimeDecision("high_volatility", False, "atr_above_max", atr_value, slope)

        if abs(slope) < self.min_slope:
            return RegimeDecision("flat", False, "slope_too_low", atr_value, slope)

        if slope > 0:
            return RegimeDecision("trend_up", True, "ok", atr_value, slope)

        if slope < 0:
            return RegimeDecision("trend_down", True, "ok", atr_value, slope)

        return RegimeDecision("normal", True, "ok", atr_value, slope)

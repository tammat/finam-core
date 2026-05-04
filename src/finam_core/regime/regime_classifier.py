# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegimeState:
    trend: str
    volatility: str
    regime: str
    atr_pct: float
    strength: float


class RegimeClassifier:
    """
    Русский комментарий:
    Простая классификация режима рынка:
    - trend: up / down / flat
    - volatility: low / normal / high
    """

    def __init__(
        self,
        min_trend_strength: float = 0.001,
        low_atr_pct: float = 0.0005,
        high_atr_pct: float = 0.003,
    ) -> None:
        self.min_trend_strength = min_trend_strength
        self.low_atr_pct = low_atr_pct
        self.high_atr_pct = high_atr_pct

    def classify(self, fast_ma: float, slow_ma: float, atr_pct: float) -> RegimeState:
        if slow_ma == 0:
            strength = 0.0
        else:
            strength = (fast_ma - slow_ma) / slow_ma

        if strength >= self.min_trend_strength:
            trend = "up"
        elif strength <= -self.min_trend_strength:
            trend = "down"
        else:
            trend = "flat"

        if atr_pct < self.low_atr_pct:
            volatility = "low_vol"
        elif atr_pct > self.high_atr_pct:
            volatility = "high_vol"
        else:
            volatility = "normal_vol"

        return RegimeState(
            trend=trend,
            volatility=volatility,
            regime=f"{trend}_{volatility}",
            atr_pct=float(atr_pct),
            strength=float(strength),
        )

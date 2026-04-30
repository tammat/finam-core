# -*- coding: utf-8 -*-

class RegimeDecision:
    def __init__(self, trend: str, volatility: str, atr: float):
        self.trend = trend
        self.volatility = volatility
        self.atr = atr

    def is_tradeable(self) -> bool:
        return self.volatility != "low" and self.trend != "flat"


class RegimeEngine:
    """
    Определяет режим рынка:
    trend + volatility
    """

    def __init__(self, min_atr_pct: float = 0.003):
        self.min_atr_pct = min_atr_pct

    def evaluate(self, price: float, features: dict) -> RegimeDecision:
        atr = float(features.get("atr", price * 0.005))
        trend = features.get("trend", "flat")

        # 🔹 волатильность
        if atr < price * self.min_atr_pct:
            volatility = "low"
        elif atr < price * self.min_atr_pct * 2:
            volatility = "normal"
        else:
            volatility = "high"

        return RegimeDecision(
            trend=trend,
            volatility=volatility,
            atr=atr,
        )
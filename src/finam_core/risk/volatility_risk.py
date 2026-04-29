# src/finam_core/risk/volatility_risk.py

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class VolatilityRiskParams:
    atr: float
    stop_abs: float
    take_abs: float
    qty: float
    risk_amount: float


class VolatilityRiskEngine:
    """
    Русский коммент: Risk v3 — ATR-aware риск и position sizing.
    Не отправляет заявки напрямую, только рассчитывает параметры.
    """

    def __init__(self):
        self.default_atr = float(os.getenv("VOL_RISK_DEFAULT_ATR", "0.10"))
        self.min_atr = float(os.getenv("VOL_RISK_MIN_ATR", "0.03"))
        self.stop_atr_mult = float(os.getenv("VOL_RISK_STOP_ATR_MULT", "1.5"))
        self.take_atr_mult = float(os.getenv("VOL_RISK_TAKE_ATR_MULT", "2.0"))
        self.risk_per_trade = float(os.getenv("VOL_RISK_PER_TRADE", "100.0"))
        self.min_qty = float(os.getenv("VOL_RISK_MIN_QTY", "1"))
        self.max_qty = float(os.getenv("VOL_RISK_MAX_QTY", "1"))

    def _clean_atr(self, atr) -> float:
        try:
            value = float(atr)
        except Exception:
            value = 0.0

        if value <= 0:
            return self.default_atr

        return value

    def compute(self, atr=None) -> VolatilityRiskParams:
        atr_value = max(self._clean_atr(atr), self.min_atr)

        stop_abs = max(atr_value * self.stop_atr_mult, 0.0001)
        take_abs = max(atr_value * self.take_atr_mult, 0.0001)

        raw_qty = self.risk_per_trade / stop_abs
        qty = max(self.min_qty, min(self.max_qty, raw_qty))

        return VolatilityRiskParams(
            atr=atr_value,
            stop_abs=stop_abs,
            take_abs=take_abs,
            qty=qty,
            risk_amount=qty * stop_abs,
        )

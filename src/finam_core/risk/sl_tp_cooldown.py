# src/finam_core/risk/sl_tp_cooldown.py

from __future__ import annotations

import os
import time
from dataclasses import dataclass


@dataclass
class ExitDecision:
    should_exit: bool
    reason: str | None = None
    side: str | None = None
    qty: float = 0.0


class SlTpCooldownEngine:
    """
    Русский коммент: Risk v2 exit-layer.
    Управляет stop-loss, take-profit и cooldown после выхода.
    Не отправляет заявки напрямую.
    """

    def __init__(self):
        self.stop_loss_abs = float(os.getenv("RISK_V2_STOP_LOSS_ABS", "0.30"))
        self.take_profit_abs = float(os.getenv("RISK_V2_TAKE_PROFIT_ABS", "0.60"))
        self.cooldown_sec = float(os.getenv("RISK_V2_COOLDOWN_SEC", "300"))
        self._cooldown_until: dict[str, float] = {}

    def is_cooldown(self, symbol: str) -> bool:
        return time.time() < self._cooldown_until.get(symbol, 0.0)

    def mark_exit(self, symbol: str) -> None:
        self._cooldown_until[symbol] = time.time() + self.cooldown_sec

    def evaluate(self, symbol: str, qty: float, avg_price: float, last_price: float) -> ExitDecision:
        if qty == 0:
            return ExitDecision(False)

        abs_qty = abs(float(qty))

        # LONG: SL при падении, TP при росте.
        if qty > 0:
            if last_price <= avg_price - self.stop_loss_abs:
                return ExitDecision(True, "stop_loss_long", "SELL", abs_qty)
            if last_price >= avg_price + self.take_profit_abs:
                return ExitDecision(True, "take_profit_long", "SELL", abs_qty)

        # SHORT: SL при росте, TP при падении.
        if qty < 0:
            if last_price >= avg_price + self.stop_loss_abs:
                return ExitDecision(True, "stop_loss_short", "BUY", abs_qty)
            if last_price <= avg_price - self.take_profit_abs:
                return ExitDecision(True, "take_profit_short", "BUY", abs_qty)

        return ExitDecision(False)

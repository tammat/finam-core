# src/finam_core/strategy/breakout_reactive.py

from __future__ import annotations

import os
from collections import deque


class BreakoutReactiveStrategy:
    """
    Русский коммент: Strategy v2 для PAPER/live тестов.
    BUY при пробое верхней границы предыдущего окна.
    SELL при пробое нижней границы предыдущего окна.
    """

    def __init__(self, symbol: str, window: int | None = None, breakout_abs: float | None = None, qty: float | None = None):
        self.symbol = symbol
        self.window = int(window if window is not None else os.getenv("STRATEGY_BREAKOUT_WINDOW", "20"))
        self.breakout_abs = float(breakout_abs if breakout_abs is not None else os.getenv("STRATEGY_BREAKOUT_ABS", "0.02"))
        self.qty = float(qty if qty is not None else os.getenv("STRATEGY_QTY", "1.0"))
        self.prices = deque(maxlen=max(self.window, 2))
        self.sent = False

    def on_quote(self, st: dict):
        if self.sent:
            return None

        sym = st.get("symbol")
        if sym != self.symbol:
            return None

        price = st.get("last")
        if price is None:
            return None

        price = float(price)

        if len(self.prices) < self.window:
            self.prices.append(price)
            return None

        prev_high = max(self.prices)
        prev_low = min(self.prices)
        self.prices.append(price)

        if price >= prev_high + self.breakout_abs:
            self.sent = True
            return {
                "symbol": sym,
                "side": "BUY",
                "qty": self.qty,
                "reason": "breakout_up",
                "price": price,
                "prev_high": prev_high,
                "breakout_abs": self.breakout_abs,
            }

        if price <= prev_low - self.breakout_abs:
            self.sent = True
            return {
                "symbol": sym,
                "side": "SELL",
                "qty": self.qty,
                "reason": "breakout_down",
                "price": price,
                "prev_low": prev_low,
                "breakout_abs": self.breakout_abs,
            }

        return None

    def mark_submitted(self) -> None:
        self.sent = True

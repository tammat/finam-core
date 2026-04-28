# -*- coding: utf-8 -*-
"""
TrailingExitEngine — управление выходом из позиции.
Русский коммент: не открывает новые позиции, только формирует SELL intent для выхода.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TrailingState:
    entry_price: float
    max_price: float
    stop_loss: float
    take_profit: float


class TrailingExitEngine:
    def __init__(self, stop_abs: float = 0.30, take_abs: float = 0.60, trail_abs: float = 0.30):
        self.stop_abs = float(stop_abs)
        self.take_abs = float(take_abs)
        self.trail_abs = float(trail_abs)
        self.states: dict[str, TrailingState] = {}

    def on_position_opened(self, symbol: str, entry_price: float) -> None:
        entry = float(entry_price)
        self.states[symbol] = TrailingState(
            entry_price=entry,
            max_price=entry,
            stop_loss=entry - self.stop_abs,
            take_profit=entry + self.take_abs,
        )

    def reset(self, symbol: str) -> None:
        self.states.pop(symbol, None)

    def evaluate_long(self, symbol: str, price: float, qty: float):
        if qty <= 0:
            self.reset(symbol)
            return None

        st = self.states.get(symbol)
        if st is None:
            self.on_position_opened(symbol, price)
            st = self.states[symbol]

        px = float(price)

        if px > st.max_price:
            st.max_price = px
            st.stop_loss = max(st.stop_loss, px - self.trail_abs)

        if px <= st.stop_loss:
            return {
                "symbol": symbol,
                "side": "SELL",
                "qty": float(qty),
                "reason": "TRAILING_STOP",
                "stop_loss": st.stop_loss,
                "take_profit": st.take_profit,
            }

        if px >= st.take_profit:
            return {
                "symbol": symbol,
                "side": "SELL",
                "qty": float(qty),
                "reason": "TAKE_PROFIT",
                "stop_loss": st.stop_loss,
                "take_profit": st.take_profit,
            }

        return None

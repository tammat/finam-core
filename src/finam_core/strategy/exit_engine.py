# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExitDecision:
    should_exit: bool
    reason: str
    stop_price: float | None = None


class ExitEngine:
    """Русский комментарий: ExitEngine только принимает решение о выходе, заявки не отправляет."""

    def __init__(
        self,
        max_bars_in_trade: int = 20,
        breakeven_atr_k: float = 1.0,
        trailing_atr_k: float = 1.5,
        stall_atr_k: float = 0.2,
    ) -> None:
        self.max_bars_in_trade = int(max_bars_in_trade)
        self.breakeven_atr_k = float(breakeven_atr_k)
        self.trailing_atr_k = float(trailing_atr_k)
        self.stall_atr_k = float(stall_atr_k)

    def evaluate(
        self,
        *,
        side: str,
        entry_price: float,
        current_price: float,
        atr: float,
        bars_held: int,
        prev_close: float | None = None,
        current_stop: float | None = None,
    ) -> ExitDecision:
        side = side.upper()
        entry = float(entry_price)
        price = float(current_price)
        atr = float(atr)

        if atr <= 0:
            return ExitDecision(False, "no_atr", current_stop)

        if bars_held >= self.max_bars_in_trade:
            return ExitDecision(True, "time_exit", current_stop)

        if side == "BUY":
            profit = price - entry

            if current_stop is not None and price <= current_stop:
                return ExitDecision(True, "stop_loss_long", current_stop)

            stop = current_stop

            if profit >= self.breakeven_atr_k * atr:
                stop = max(stop or entry, entry)

            if profit >= self.trailing_atr_k * atr:
                stop = max(stop or entry, price - self.trailing_atr_k * atr)

            if prev_close is not None and abs(price - float(prev_close)) < self.stall_atr_k * atr and profit > 0:
                return ExitDecision(True, "stall_exit_long", stop)

            return ExitDecision(False, "hold_long", stop)

        if side == "SELL":
            profit = entry - price

            if current_stop is not None and price >= current_stop:
                return ExitDecision(True, "stop_loss_short", current_stop)

            stop = current_stop

            if profit >= self.breakeven_atr_k * atr:
                stop = min(stop or entry, entry)

            if profit >= self.trailing_atr_k * atr:
                stop = min(stop or entry, price + self.trailing_atr_k * atr)

            if prev_close is not None and abs(price - float(prev_close)) < self.stall_atr_k * atr and profit > 0:
                return ExitDecision(True, "stall_exit_short", stop)

            return ExitDecision(False, "hold_short", stop)

        return ExitDecision(False, "unknown_side", current_stop)

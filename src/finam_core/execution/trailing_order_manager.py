# -*- coding: utf-8 -*-
"""
TrailingOrderManager — robot-side trailing stop manager.
Русский комментарий: модуль только рассчитывает действие по защитной stop-заявке.
Заявки брокеру не отправляет.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrailingOrderDecision:
    action: str
    symbol: str
    side: str
    qty: float
    stop_price: float | None
    reason: str


class TrailingOrderManager:
    def __init__(self, trail_abs: float = 0.40, min_replace_step: float = 0.10) -> None:
        self.trail_abs = float(trail_abs)
        self.min_replace_step = float(min_replace_step)

    def evaluate_long(
        self,
        *,
        symbol: str,
        qty: float,
        last_price: float,
        current_stop: float | None = None,
    ) -> TrailingOrderDecision:
        qty = float(qty or 0.0)
        last = float(last_price)

        if qty <= 0:
            return TrailingOrderDecision("HOLD", symbol, "SELL", qty, current_stop, "no_long_position")

        new_stop = round(last - self.trail_abs, 2)

        if current_stop is None:
            return TrailingOrderDecision("PLACE_STOP", symbol, "SELL", qty, new_stop, "initial_trailing_stop")

        old_stop = float(current_stop)

        if new_stop <= old_stop:
            return TrailingOrderDecision("HOLD", symbol, "SELL", qty, old_stop, "stop_not_improved")

        if new_stop - old_stop < self.min_replace_step:
            return TrailingOrderDecision("HOLD", symbol, "SELL", qty, old_stop, "replace_step_too_small")

        return TrailingOrderDecision("REPLACE_STOP", symbol, "SELL", qty, new_stop, "trailing_stop_improved")

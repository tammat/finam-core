# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Candle:
    open: float
    high: float
    low: float
    close: float


def is_knife_bar(
    candle: Candle,
    prev_close: float,
    atr: float,
    *,
    move_atr_k: float = 1.5,
    range_atr_k: float = 2.0,
) -> bool:
    """Русский комментарий: определяет резкий импульс/шпильку по ATR."""
    if atr <= 0:
        return False

    move = abs(float(candle.close) - float(prev_close))
    candle_range = float(candle.high) - float(candle.low)

    return (move > float(move_atr_k) * atr) or (candle_range > float(range_atr_k) * atr)


class KnifeState:
    """Русский комментарий: хранит cooldown после ножа, чтобы не входить по первому импульсу."""

    def __init__(self, cooldown_bars: int = 3) -> None:
        self.cooldown_bars = int(cooldown_bars)
        self.cooldown_left = 0
        self.last_knife_side: str | None = None

    def on_bar(self, is_knife: bool, side: str | None = None) -> None:
        if is_knife:
            self.cooldown_left = self.cooldown_bars
            self.last_knife_side = side
            return

        if self.cooldown_left > 0:
            self.cooldown_left -= 1

    def is_blocked(self) -> bool:
        return self.cooldown_left > 0

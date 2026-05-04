# -*- coding: utf-8 -*-
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime


@dataclass
class BrSignal:
    symbol: str
    side: str
    price: float
    stop: float
    take: float
    ts: datetime
    reason: str


class BrConservativeBreakout:
    """
    BR_CONSERVATIVE_BREAKOUT_M5.
    Русский комментарий: стратегия только генерирует сигнал, заявки не отправляет.
    """

    def __init__(
        self,
        symbol: str = "BRM6@RTSX",
        breakout_window: int = 20,
        atr_period: int = 14,
        stop_atr: float = 2.5,
        take_atr: float = 2.5,
        regime_fast: int = 5,
        regime_slow: int = 20,
        regime_min_strength: float = 0.001,
        regime_min_atr_pct: float = 0.0003,
        regime_max_atr_pct: float = 0.005,
    ) -> None:
        self.symbol = symbol
        self.breakout_window = breakout_window
        self.atr_period = atr_period
        self.stop_atr = stop_atr
        self.take_atr = take_atr

        self.regime_fast = regime_fast
        self.regime_slow = regime_slow
        self.regime_min_strength = regime_min_strength
        self.regime_min_atr_pct = regime_min_atr_pct
        self.regime_max_atr_pct = regime_max_atr_pct

        self.highs: deque[float] = deque(maxlen=breakout_window)
        self.lows: deque[float] = deque(maxlen=breakout_window)
        self.tr_values: deque[float] = deque(maxlen=atr_period)

        self.prev_close: float | None = None

        self.regime_ema_fast: float | None = None
        self.regime_ema_slow: float | None = None
        self.regime_tr_values: deque[float] = deque(maxlen=14)
        self.regime_prev_close: float | None = None
        self.regime_direction: int = 0

    @staticmethod
    def _ema(prev: float | None, value: float, period: int) -> float:
        if prev is None:
            return value
        alpha = 2.0 / (period + 1.0)
        return alpha * value + (1.0 - alpha) * prev

    @staticmethod
    def _true_range(high: float, low: float, prev_close: float | None) -> float:
        if prev_close is None:
            return high - low
        return max(high - low, abs(high - prev_close), abs(low - prev_close))

    def on_regime_bar(self, ts: datetime, open_: float, high: float, low: float, close: float, volume: float = 0.0) -> None:
        tr = self._true_range(high, low, self.regime_prev_close)
        self.regime_prev_close = close
        self.regime_tr_values.append(tr)

        self.regime_ema_fast = self._ema(self.regime_ema_fast, close, self.regime_fast)
        self.regime_ema_slow = self._ema(self.regime_ema_slow, close, self.regime_slow)

        atr = sum(self.regime_tr_values) / len(self.regime_tr_values)
        atr_pct = atr / close if close else 0.0
        strength = abs(self.regime_ema_fast - self.regime_ema_slow) / close if close else 0.0

        self.regime_direction = 0
        if self.regime_min_atr_pct <= atr_pct <= self.regime_max_atr_pct and strength >= self.regime_min_strength:
            if self.regime_ema_fast > self.regime_ema_slow:
                self.regime_direction = 1
            elif self.regime_ema_fast < self.regime_ema_slow:
                self.regime_direction = -1

    def on_signal_bar(self, ts: datetime, open_: float, high: float, low: float, close: float, volume: float = 0.0) -> BrSignal | None:
        tr = self._true_range(high, low, self.prev_close)
        self.prev_close = close
        self.tr_values.append(tr)

        signal: BrSignal | None = None

        if len(self.highs) >= self.breakout_window and len(self.lows) >= self.breakout_window and len(self.tr_values) >= self.atr_period:
            range_high = max(self.highs)
            range_low = min(self.lows)
            atr = sum(self.tr_values) / len(self.tr_values)

            if close > range_high and self.regime_direction == 1:
                signal = BrSignal(
                    symbol=self.symbol,
                    side="BUY",
                    price=close,
                    stop=close - atr * self.stop_atr,
                    take=close + atr * self.take_atr,
                    ts=ts,
                    reason="BR_M5_BREAKOUT_UP_M15_REGIME_OK",
                )

            elif close < range_low and self.regime_direction == -1:
                signal = BrSignal(
                    symbol=self.symbol,
                    side="SELL",
                    price=close,
                    stop=close + atr * self.stop_atr,
                    take=close - atr * self.take_atr,
                    ts=ts,
                    reason="BR_M5_BREAKOUT_DOWN_M15_REGIME_OK",
                )

        self.highs.append(high)
        self.lows.append(low)

        return signal

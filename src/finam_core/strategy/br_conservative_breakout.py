# -*- coding: utf-8 -*-
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime


@dataclass
class BrOnlineParams:
    """Русский комментарий: online-параметры BR-стратегии, выбранные по regime/volatility."""
    mode: str
    breakout_window: int
    stop_atr: float
    take_atr: float
    allow_trade: bool
    reason: str


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
        signal_cooldown_bars: int = 12,
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

        # Русский комментарий: подавление повторных сигналов, чтобы replay/live не спамили одинаковыми входами.
        self.signal_cooldown_bars = signal_cooldown_bars
        self.cooldown_counter = 0
        self.last_signal_side: str | None = None

        self.highs: deque[float] = deque(maxlen=breakout_window)
        self.lows: deque[float] = deque(maxlen=breakout_window)
        self.tr_values: deque[float] = deque(maxlen=atr_period)

        self.prev_close: float | None = None

        self.regime_ema_fast: float | None = None
        self.regime_ema_slow: float | None = None
        self.regime_tr_values: deque[float] = deque(maxlen=14)
        self.regime_prev_close: float | None = None
        self.regime_direction: int = 0
        self.current_params = BrOnlineParams(
            mode="initial",
            breakout_window=self.breakout_window,
            stop_atr=self.stop_atr,
            take_atr=self.take_atr,
            allow_trade=False,
            reason="WARMUP",
        )
        self.regime_atr_pct: float = 0.0
        self.regime_strength: float = 0.0

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

    def _select_online_params(self, atr_pct: float, strength: float) -> BrOnlineParams:
        """Русский комментарий: выбирает параметры breakout по текущему режиму M15 без переобучения на тиках."""
        if self.regime_direction == 0:
            return BrOnlineParams(
                mode="no_trade",
                breakout_window=self.breakout_window,
                stop_atr=self.stop_atr,
                take_atr=self.take_atr,
                allow_trade=False,
                reason="REGIME_NEUTRAL",
            )

        if atr_pct < self.regime_min_atr_pct:
            return BrOnlineParams(
                mode="no_trade",
                breakout_window=self.breakout_window,
                stop_atr=self.stop_atr,
                take_atr=self.take_atr,
                allow_trade=False,
                reason="ATR_TOO_LOW",
            )

        if atr_pct > self.regime_max_atr_pct:
            return BrOnlineParams(
                mode="no_trade",
                breakout_window=self.breakout_window,
                stop_atr=self.stop_atr,
                take_atr=self.take_atr,
                allow_trade=False,
                reason="ATR_TOO_HIGH",
            )

        if strength < self.regime_min_strength:
            return BrOnlineParams(
                mode="no_trade",
                breakout_window=self.breakout_window,
                stop_atr=self.stop_atr,
                take_atr=self.take_atr,
                allow_trade=False,
                reason="TREND_STRENGTH_LOW",
            )

        # Русский комментарий: консервативные preset-режимы, подтверждённые walk-forward.
        if atr_pct >= 0.003:
            return BrOnlineParams(
                mode="trend_high_vol",
                breakout_window=30,
                stop_atr=2.0,
                take_atr=3.0,
                allow_trade=True,
                reason="HIGH_VOL_TREND_PRESET",
            )

        if strength >= 0.002:
            return BrOnlineParams(
                mode="strong_trend",
                breakout_window=30,
                stop_atr=1.5,
                take_atr=2.5,
                allow_trade=True,
                reason="STRONG_TREND_PRESET",
            )

        return BrOnlineParams(
            mode="normal",
            breakout_window=20,
            stop_atr=2.5,
            take_atr=2.5,
            allow_trade=True,
            reason="NORMAL_REGIME_PRESET",
        )

    def on_regime_bar(self, ts: datetime, open_: float, high: float, low: float, close: float, volume: float = 0.0) -> None:
        tr = self._true_range(high, low, self.regime_prev_close)
        self.regime_prev_close = close
        self.regime_tr_values.append(tr)

        self.regime_ema_fast = self._ema(self.regime_ema_fast, close, self.regime_fast)
        self.regime_ema_slow = self._ema(self.regime_ema_slow, close, self.regime_slow)

        atr = sum(self.regime_tr_values) / len(self.regime_tr_values)
        atr_pct = atr / close if close else 0.0
        strength = abs(self.regime_ema_fast - self.regime_ema_slow) / close if close else 0.0

        self.regime_atr_pct = atr_pct
        self.regime_strength = strength

        self.regime_direction = 0
        if self.regime_min_atr_pct <= atr_pct <= self.regime_max_atr_pct and strength >= self.regime_min_strength:
            if self.regime_ema_fast > self.regime_ema_slow:
                self.regime_direction = 1
            elif self.regime_ema_fast < self.regime_ema_slow:
                self.regime_direction = -1

        self.current_params = self._select_online_params(atr_pct=atr_pct, strength=strength)
        self.breakout_window = self.current_params.breakout_window
        self.highs = deque(self.highs, maxlen=self.breakout_window)
        self.lows = deque(self.lows, maxlen=self.breakout_window)

    def _signal_blocked_by_cooldown(self, side: str) -> bool:
        """Русский комментарий: блокируем повторный сигнал в ту же сторону во время cooldown."""
        return self.cooldown_counter > 0 and self.last_signal_side == side

    def _register_signal(self, side: str) -> None:
        """Русский комментарий: фиксируем сторону сигнала и запускаем cooldown."""
        self.last_signal_side = side
        self.cooldown_counter = self.signal_cooldown_bars

    def on_signal_bar(self, ts: datetime, open_: float, high: float, low: float, close: float, volume: float = 0.0) -> BrSignal | None:
        tr = self._true_range(high, low, self.prev_close)
        self.prev_close = close
        self.tr_values.append(tr)

        signal: BrSignal | None = None
        if self.cooldown_counter > 0:
            self.cooldown_counter -= 1

        if not self.current_params.allow_trade:
            self.highs.append(high)
            self.lows.append(low)
            return None

        if len(self.highs) >= self.breakout_window and len(self.lows) >= self.breakout_window and len(self.tr_values) >= self.atr_period:
            range_high = max(self.highs)
            range_low = min(self.lows)
            atr = sum(self.tr_values) / len(self.tr_values)
            stop_atr = self.current_params.stop_atr
            take_atr = self.current_params.take_atr

            if close > range_high and self.regime_direction == 1 and not self._signal_blocked_by_cooldown("BUY"):
                signal = BrSignal(
                    symbol=self.symbol,
                    side="BUY",
                    price=close,
                    stop=close - atr * stop_atr,
                    take=close + atr * take_atr,
                    ts=ts,
                    reason=f"BR_M5_BREAKOUT_UP_{self.current_params.mode}_{self.current_params.reason}",
                )
                self._register_signal("BUY")

            elif close < range_low and self.regime_direction == -1 and not self._signal_blocked_by_cooldown("SELL"):
                signal = BrSignal(
                    symbol=self.symbol,
                    side="SELL",
                    price=close,
                    stop=close + atr * stop_atr,
                    take=close - atr * take_atr,
                    ts=ts,
                    reason=f"BR_M5_BREAKOUT_DOWN_{self.current_params.mode}_{self.current_params.reason}",
                )
                self._register_signal("SELL")

        self.highs.append(high)
        self.lows.append(low)

        return signal

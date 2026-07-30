# -*- coding: utf-8 -*-
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from statistics import median


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
    atr: float = 0.0
    stop_atr_used: float = 0.0
    take_atr_used: float = 0.0
    volume_ratio: float = 0.0


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
        enable_rsi_filter: bool = True,
        enable_paper_adaptive_risk: bool = False,
        volume_window: int = 20,
        min_volume_ratio: float = 1.3,
        min_stop_atr: float = 1.8,
        max_stop_atr: float = 2.5,
        structure_buffer_atr: float = 0.25,
        min_reward_r: float = 1.5,
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

        # Русский комментарий: подавление повторных сигналов в одном и том же режиме рынка.
        self.signal_cooldown_bars = signal_cooldown_bars
        self.enable_rsi_filter = enable_rsi_filter
        self.enable_paper_adaptive_risk = bool(enable_paper_adaptive_risk)
        self.volume_window = max(5, int(volume_window))
        self.min_volume_ratio = max(1.0, float(min_volume_ratio))
        self.min_stop_atr = max(0.1, float(min_stop_atr))
        self.max_stop_atr = max(self.min_stop_atr, float(max_stop_atr))
        self.structure_buffer_atr = max(0.0, float(structure_buffer_atr))
        self.min_reward_r = max(1.0, float(min_reward_r))
        self.volumes: deque[float] = deque(maxlen=self.volume_window)
        self.last_volume_ratio: float = 0.0
        self.volume_filter_reason: str = "DISABLED"
        self.cooldown_counter = 0
        self.last_signal_side: str | None = None
        self.last_signal_regime_direction: int | None = None
        self._previous_regime_direction: int = 0

        self.highs: deque[float] = deque(maxlen=breakout_window)
        self.lows: deque[float] = deque(maxlen=breakout_window)
        self.tr_values: deque[float] = deque(maxlen=atr_period)

        self.prev_close: float | None = None

        self.regime_ema_fast: float | None = None
        self.regime_ema_slow: float | None = None
        self.regime_tr_values: deque[float] = deque(maxlen=14)
        self.regime_closes: deque[float] = deque(maxlen=15)
        self.regime_prev_close: float | None = None
        self.regime_rsi: float | None = None
        self.regime_rsi_state: str = "WARMUP"
        self.rsi_filter_passed: bool = False
        self.rsi_filter_reason: str = "RSI_WARMUP"
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
        self.regime_closes.append(float(close))
        if len(self.regime_closes) >= 15:
            changes = [current - previous for previous, current in
                       zip(self.regime_closes, list(self.regime_closes)[1:])]
            gains = sum(max(change, 0.0) for change in changes) / len(changes)
            losses = sum(max(-change, 0.0) for change in changes) / len(changes)
            self.regime_rsi = 100.0 if losses == 0 else 100.0 - 100.0 / (1.0 + gains / losses)
            self.regime_rsi_state = "READY"

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

        # Русский комментарий: при смене направления режима разрешаем новый сигнал.
        if self.regime_direction != self._previous_regime_direction:
            self.last_signal_side = None
            self.last_signal_regime_direction = None
            self.cooldown_counter = 0
        self._previous_regime_direction = self.regime_direction

        self.current_params = self._select_online_params(atr_pct=atr_pct, strength=strength)
        self.breakout_window = self.current_params.breakout_window
        self.highs = deque(self.highs, maxlen=self.breakout_window)
        self.lows = deque(self.lows, maxlen=self.breakout_window)

    def _rsi_filter_allows(self, side: str) -> bool:
        """Русский комментарий: RSI подтверждает направление импульса старшего ТФ."""
        if not getattr(self, "enable_rsi_filter", True):
            self.rsi_filter_passed = True
            self.rsi_filter_reason = "RSI_FILTER_DISABLED"
            return True

        if self.regime_rsi is None:
            self.rsi_filter_passed = False
            self.rsi_filter_reason = "RSI_WARMUP"
            return False

        if side == "BUY":
            passed = self.regime_rsi >= 50.0
            self.rsi_filter_passed = passed
            self.rsi_filter_reason = "RSI_BUY_OK" if passed else "RSI_BUY_BLOCK"
            return passed

        if side == "SELL":
            passed = self.regime_rsi <= 50.0
            self.rsi_filter_passed = passed
            self.rsi_filter_reason = "RSI_SELL_OK" if passed else "RSI_SELL_BLOCK"
            return passed

        self.rsi_filter_passed = False
        self.rsi_filter_reason = "RSI_UNKNOWN_SIDE"
        return False

    def _signal_blocked_by_cooldown(self, side: str) -> bool:
        """Русский комментарий: блокируем повторный сигнал на заданное число M5-свечей."""
        return self.last_signal_side == side and self.cooldown_counter > 0

    def _register_signal(self, side: str) -> None:
        """Русский комментарий: фиксируем сторону сигнала до смены режима."""
        self.last_signal_side = side
        self.last_signal_regime_direction = self.regime_direction
        self.cooldown_counter = self.signal_cooldown_bars

    def on_signal_bar(self, ts: datetime, open_: float, high: float, low: float, close: float, volume: float = 0.0) -> BrSignal | None:
        if self.cooldown_counter > 0:
            self.cooldown_counter -= 1
        tr = self._true_range(high, low, self.prev_close)
        self.prev_close = close
        self.tr_values.append(tr)

        signal: BrSignal | None = None

        if not self.current_params.allow_trade:
            self.highs.append(high)
            self.lows.append(low)
            if float(volume or 0.0) > 0:
                self.volumes.append(float(volume))
            return None

        if len(self.highs) >= self.breakout_window and len(self.lows) >= self.breakout_window and len(self.tr_values) >= self.atr_period:
            range_high = max(self.highs)
            range_low = min(self.lows)
            atr = sum(self.tr_values) / len(self.tr_values)
            stop_atr = self.current_params.stop_atr
            take_atr = self.current_params.take_atr

            volume_ratio = 0.0
            volume_confirmed = True
            if self.enable_paper_adaptive_risk:
                positive_history = [value for value in self.volumes if value > 0]
                if len(positive_history) < self.volume_window:
                    volume_confirmed = False
                    self.volume_filter_reason = "VOLUME_WARMUP"
                else:
                    baseline_volume = float(median(positive_history))
                    volume_ratio = float(volume) / baseline_volume if baseline_volume > 0 else 0.0
                    volume_confirmed = volume_ratio >= self.min_volume_ratio
                    self.volume_filter_reason = (
                        "VOLUME_CONFIRMED" if volume_confirmed else "VOLUME_BELOW_THRESHOLD"
                    )
                self.last_volume_ratio = volume_ratio

            if (close > range_high and self.regime_direction == 1
                    and self._rsi_filter_allows("BUY")
                    and not self._signal_blocked_by_cooldown("BUY") and volume_confirmed):
                if self.enable_paper_adaptive_risk:
                    structural_distance = close - (range_high - atr * self.structure_buffer_atr)
                    stop_distance = min(
                        max(structural_distance, atr * self.min_stop_atr),
                        atr * self.max_stop_atr,
                    )
                    take_distance = max(atr * take_atr, stop_distance * self.min_reward_r)
                    stop_atr = stop_distance / atr
                    take_atr = take_distance / atr
                else:
                    stop_distance = atr * stop_atr
                    take_distance = atr * take_atr
                signal = BrSignal(
                    symbol=self.symbol,
                    side="BUY",
                    price=close,
                    stop=close - stop_distance,
                    take=close + take_distance,
                    ts=ts,
                    reason=f"BR_M5_BREAKOUT_UP_{self.current_params.mode}_{self.current_params.reason}",
                    atr=atr,
                    stop_atr_used=stop_atr,
                    take_atr_used=take_atr,
                    volume_ratio=volume_ratio,
                )
                self._register_signal("BUY")

            elif (close < range_low and self.regime_direction == -1
                    and self._rsi_filter_allows("SELL")
                    and not self._signal_blocked_by_cooldown("SELL") and volume_confirmed):
                if self.enable_paper_adaptive_risk:
                    structural_distance = (range_low + atr * self.structure_buffer_atr) - close
                    stop_distance = min(
                        max(structural_distance, atr * self.min_stop_atr),
                        atr * self.max_stop_atr,
                    )
                    take_distance = max(atr * take_atr, stop_distance * self.min_reward_r)
                    stop_atr = stop_distance / atr
                    take_atr = take_distance / atr
                else:
                    stop_distance = atr * stop_atr
                    take_distance = atr * take_atr
                signal = BrSignal(
                    symbol=self.symbol,
                    side="SELL",
                    price=close,
                    stop=close + stop_distance,
                    take=close - take_distance,
                    ts=ts,
                    reason=f"BR_M5_BREAKOUT_DOWN_{self.current_params.mode}_{self.current_params.reason}",
                    atr=atr,
                    stop_atr_used=stop_atr,
                    take_atr_used=take_atr,
                    volume_ratio=volume_ratio,
                )
                self._register_signal("SELL")

        self.highs.append(high)
        self.lows.append(low)
        if float(volume or 0.0) > 0:
            self.volumes.append(float(volume))

        return signal

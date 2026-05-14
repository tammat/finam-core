from __future__ import annotations

import os
import time
from collections import deque


class MeanReversionEquity:

    """
    Русский комментарий:
    Mean-reversion стратегия для акций MOEX.

    Логика:
    - отклонение от VWAP
    - ATR filter
    - cooldown
    - reversal bounce
    """

    def __init__(self):

        self.window = int(os.getenv("MR_WINDOW", "30"))

        self.min_deviation_pct = float(
            os.getenv("MR_MIN_DEVIATION_PCT", "0.003")
        )

        self.cooldown_sec = int(
            os.getenv("MR_COOLDOWN_SEC", "120")
        )

        self.min_atr_pct = float(
            os.getenv("MR_MIN_ATR_PCT", "0.001")
        )

        self.last_signal_ts = {}

        self.prices = {}
        self.volumes = {}

    def _push(self, storage, symbol, value):

        if symbol not in storage:
            storage[symbol] = deque(maxlen=self.window)

        storage[symbol].append(value)

    def _vwap(self, symbol):

        prices = self.prices.get(symbol)
        volumes = self.volumes.get(symbol)

        if not prices or not volumes:
            return None

        if len(prices) < 5:
            return None

        total_volume = sum(volumes)

        if total_volume <= 0:
            return None

        weighted = 0.0

        for p, v in zip(prices, volumes):
            weighted += p * v

        return weighted / total_volume

    def on_quote(self, state: dict):

        symbol = str(state.get("symbol"))

        price = float(
            state.get("last")
            or state.get("price")
            or 0.0
        )

        if price <= 0:
            return None

        volume = float(
            state.get("volume")
            or 1.0
        )

        atr = float(
            state.get("atr")
            or abs(price * 0.003)
        )

        atr_pct = atr / max(price, 1e-9)

        if atr_pct < self.min_atr_pct:
            return None

        self._push(self.prices, symbol, price)
        self._push(self.volumes, symbol, volume)

        vwap = self._vwap(symbol)

        if vwap is None:
            return None

        deviation_pct = (price - vwap) / max(vwap, 1e-9)

        now = time.time()

        last_ts = self.last_signal_ts.get(symbol, 0)

        if (now - last_ts) < self.cooldown_sec:
            return None

        signal = None

        # Русский комментарий:
        # mean reversion BUY.
        if deviation_pct <= -self.min_deviation_pct:

            signal = {
                "symbol": symbol,
                "side": "BUY",
                "qty": 1.0,
                "price": price,
                "reason": "mr_long_reversion",
                "strategy": "MEAN_REVERSION_EQUITY",
                "confidence": min(
                    1.0,
                    abs(deviation_pct) * 100,
                ),
                "features": {
                    "atr": atr,
                    "atr_pct": atr_pct,
                    "vwap": vwap,
                    "deviation_pct": deviation_pct,
                },
            }

        # Русский комментарий:
        # mean reversion SELL.
        elif deviation_pct >= self.min_deviation_pct:

            signal = {
                "symbol": symbol,
                "side": "SELL",
                "qty": 1.0,
                "price": price,
                "reason": "mr_short_reversion",
                "strategy": "MEAN_REVERSION_EQUITY",
                "confidence": min(
                    1.0,
                    abs(deviation_pct) * 100,
                ),
                "features": {
                    "atr": atr,
                    "atr_pct": atr_pct,
                    "vwap": vwap,
                    "deviation_pct": deviation_pct,
                },
            }

        if signal is not None:
            self.last_signal_ts[symbol] = now

        return signal

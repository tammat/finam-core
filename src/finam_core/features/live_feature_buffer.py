# -*- coding: utf-8 -*-
"""
LiveFeatureBuffer — собирает признаки из потока QUOTE.

Задача:
- хранить последние N баров
- считать:
    - true_range
    - ATR
    - range_atr
    - EMA
"""

from collections import deque
import pandas as pd


class LiveFeatureBuffer:
    def __init__(self, maxlen=200):
        self.maxlen = maxlen

        self.close = deque(maxlen=maxlen)
        self.high = deque(maxlen=maxlen)
        self.low = deque(maxlen=maxlen)

    def update(self, quote: dict):
        price = quote.get("last")

        if price is None:
            return

        px = float(price)

        # упрощённо: используем last как OHLC
        self.close.append(px)
        self.high.append(px)
        self.low.append(px)

    def ready(self) -> bool:
        # Русский коммент: для range_atr нужен запас истории под rolling range/ATR.
        return len(self.close) >= 60

    def compute(self):
        if not self.ready():
            return None

        close = pd.Series(self.close)
        high = pd.Series(self.high)
        low = pd.Series(self.low)

        # --- true range ---
        prev_close = close.shift(1)
        tr = pd.concat([
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)

        # --- ATR ---
        atr = tr.rolling(14).mean()

        # --- range ---
        rng = high.rolling(50).max() - low.rolling(50).min()

        # --- range/atr ---
        # Русский коммент: QUOTE даёт last, а не полноценный OHLC-бар.
        # Поэтому ATR может быть почти нулевым. Ставим floor от цены.
        atr_floor = close.abs() * 0.0005
        atr_safe = atr.where(atr > atr_floor, atr_floor)
        range_atr = rng / atr_safe.replace(0, 1e-9)

        # --- EMA ---
        ema = close.ewm(span=50, adjust=False).mean()

        return {
            "range_atr": range_atr.iloc[-1],
            "ema": ema,
        }
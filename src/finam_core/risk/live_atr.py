# src/finam_core/risk/live_atr.py

from __future__ import annotations

from collections import deque


class LiveAtrEstimator:
    """
    Русский коммент: простой live ATR estimator по потоку last-price.
    Не зависит от свечей: оценивает среднее абсолютное изменение цены.
    """

    def __init__(self, window: int = 20, default_atr: float = 0.10, min_atr: float = 0.03):
        self.window = max(int(window), 2)
        self.default_atr = float(default_atr)
        self.min_atr = float(min_atr)
        self.prev_price: float | None = None
        self.moves = deque(maxlen=self.window)

    def update(self, price) -> float:
        try:
            px = float(price)
        except Exception:
            return self.value()

        if self.prev_price is None:
            self.prev_price = px
            return self.value()

        move = abs(px - self.prev_price)
        self.prev_price = px
        self.moves.append(move)

        return self.value()

    def value(self) -> float:
        if not self.moves:
            return self.default_atr
        return max(sum(self.moves) / len(self.moves), self.min_atr)

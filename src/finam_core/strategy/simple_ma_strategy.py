from collections import deque
from dataclasses import dataclass


@dataclass
class Signal:
    side: str
    qty: float

    def to_fill(self, price: float):
        class Fill:
            def __init__(self, side, qty, price):
                self.fill_id = f"SMA_{price}"
                self.side = side
                self.qty = qty
                self.price = price
                self.commission = 0.0
        return Fill(self.side, self.qty, price)


class SimpleMAStrategy:

    def __init__(self, fast=5, slow=20, qty=1):
        if fast >= slow:
            raise ValueError("fast MA must be < slow MA")

        self.fast = fast
        self.slow = slow
        self.qty = qty

        self.fast_window = deque(maxlen=fast)
        self.slow_window = deque(maxlen=slow)

        self.prev_fast = None
        self.prev_slow = None

    def on_bar(self, bar, equity):

        self.fast_window.append(bar.close)
        self.slow_window.append(bar.close)

        if len(self.slow_window) < self.slow:
            return None

        fast_ma = sum(self.fast_window) / len(self.fast_window)
        slow_ma = sum(self.slow_window) / len(self.slow_window)

        signal = None

        if self.prev_fast is not None and self.prev_slow is not None:

            # Golden cross
            if self.prev_fast <= self.prev_slow and fast_ma > slow_ma:
                signal = Signal("BUY", self.qty)

            # Death cross
            elif self.prev_fast >= self.prev_slow and fast_ma < slow_ma:
                signal = Signal("SELL", self.qty)

        self.prev_fast = fast_ma
        self.prev_slow = slow_ma

        return signal
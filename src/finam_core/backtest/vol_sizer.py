from collections import deque
import math


class VolatilitySizer:

    def __init__(self, target_vol=0.02, window=20, max_leverage=3.0):
        self.target_vol = target_vol
        self.window = window
        self.max_leverage = max_leverage
        self.returns = deque(maxlen=window)

    def update(self, price, prev_price):
        if prev_price is None:
            return None

        r = (price - prev_price) / prev_price
        self.returns.append(r)

        if len(self.returns) < self.window:
            return None

        vol = math.sqrt(sum(x*x for x in self.returns) / len(self.returns))
        return vol

    def size(self, equity, price, current_vol):

        if current_vol is None or current_vol == 0:
            return 0.0

        leverage = min(self.target_vol / current_vol, self.max_leverage)

        position_value = equity * leverage
        qty = position_value / price

        return max(qty, 0.0)
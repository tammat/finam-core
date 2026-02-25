from strategy.signal import Signal
from strategy.base_strategy import BaseStrategy


class SimpleMomentumStrategy(BaseStrategy):

    def __init__(self, symbol: str, quantity: float = 1.0):
        self.symbol = symbol
        self.quantity = quantity
        self._prices = []

    def update_prices(self, prices):
        self._prices = prices

    def generate(self):
        if len(self._prices) < 2:
            return None

        last = self._prices[-1]
        prev = self._prices[-2]

        if last > prev:
            return Signal(self.symbol, "BUY", self.quantity)

        if last < prev:
            return Signal(self.symbol, "SELL", self.quantity)

        return None
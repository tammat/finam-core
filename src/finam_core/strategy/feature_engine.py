from collections import deque
import numpy as np


class FeatureEngine:
    """
    Deterministic rolling feature engine.
    Window-aware. No hardcoded indices.
    """

    def __init__(self, window=50):
        self.window = window
        self.prices = deque(maxlen=window)

    # ------------------------
    # PUBLIC API
    # ------------------------

    def update(self, price):
        self.prices.append(price)

    def ready(self):
        return len(self.prices) >= self.window

    def compute(self):
        if not self.ready():
            return None

        prices = np.array(self.prices)

        returns = np.diff(prices) / prices[:-1]

        # dynamic windows
        short_win = min(10, len(returns))
        mid_win = min(20, len(prices))

        features = {
            "return_1": returns[-1],
            "return_mean": np.mean(returns[-short_win:]),
            "volatility": np.std(returns[-short_win:]),
            "z_score": self._zscore(prices[-mid_win:]),
            "momentum": prices[-1] - prices[-mid_win],
        }

        return features

    # ------------------------
    # INTERNAL
    # ------------------------

    def _zscore(self, window):
        mean = np.mean(window)
        std = np.std(window)

        if std == 0:
            return 0.0

        return (window[-1] - mean) / std
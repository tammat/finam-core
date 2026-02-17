# Комментарии:
# Forward-looking label generation without leakage.
# Работает с numpy массивом цен.
# label[t] = sign(price[t+H] - price[t])

import numpy as np


class LabelEngine:

    def __init__(self, horizon=5):
        self.horizon = horizon

    def binary_labels(self, prices):

        prices = np.asarray(prices)

        future_prices = np.roll(prices, -self.horizon)

        future_return = future_prices - prices

        labels = np.where(
            future_return > 0, 1,
            np.where(future_return < 0, -1, 0)
        )

        # Удаляем последние horizon значений
        labels[-self.horizon:] = 0

        return labels
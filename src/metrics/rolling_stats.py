from collections import deque
from math import sqrt


class RollingStats:

    def __init__(self, window: int = 100):
        self.window = window
        self.values = deque(maxlen=window)

    def add(self, value: float):
        self.values.append(value)

    @property
    def mean(self) -> float:
        if not self.values:
            return 0.0
        return sum(self.values) / len(self.values)

    @property
    def std(self) -> float:
        if len(self.values) < 2:
            return 0.0
        m = self.mean
        var = sum((x - m) ** 2 for x in self.values) / len(self.values)
        return sqrt(var)

    @property
    def sharpe(self) -> float:
        s = self.std
        if s == 0:
            return 0.0
        return self.mean / s
from metrics.rolling_stats import RollingStats


class PerformanceTracker:

    def __init__(self, window: int = 100):
        self.returns = RollingStats(window)
        self.equity_curve = []
        self.max_equity = 0.0

    def update(self, equity: float):
        if self.equity_curve:
            prev = self.equity_curve[-1]
            if prev != 0:
                ret = (equity - prev) / prev
                self.returns.add(ret)

        self.equity_curve.append(equity)
        self.max_equity = max(self.max_equity, equity)

    @property
    def drawdown(self) -> float:
        if not self.equity_curve:
            return 0.0
        current = self.equity_curve[-1]
        if self.max_equity == 0:
            return 0.0
        return (current - self.max_equity) / self.max_equity

    @property
    def sharpe(self) -> float:
        return self.returns.sharpe
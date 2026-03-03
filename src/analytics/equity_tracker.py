# analytics/equity_tracker.py

class EquityTracker:

    def __init__(self, initial_equity: float):
        self.initial_equity = initial_equity
        self.equity = initial_equity
        self.history = [initial_equity]

    def apply_trade(self, trade):
        self.equity += trade.pnl
        self.history.append(self.equity)

    def max_drawdown(self):
        peak = self.history[0]
        max_dd = 0

        for value in self.history:
            peak = max(peak, value)
            dd = peak - value
            max_dd = max(max_dd, dd)

        return max_dd
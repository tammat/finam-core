import math


class PortfolioVolController:
    """
    L1: portfolio-level realized volatility targeting.

    - Call update(equity) each cycle (after accounting update).
    - Call multiplier() to get sizing multiplier to hit target_vol.
    - Multiplier is clamped to [min_multiplier, max_multiplier].
    """

    def __init__(
        self,
        target_vol: float,
        window: int = 50,
        min_multiplier: float = 0.25,
        max_multiplier: float = 2.0,
    ):
        self.target_vol = float(target_vol)
        self.window = int(window)
        self.min_multiplier = float(min_multiplier)
        self.max_multiplier = float(max_multiplier)

        self.returns = []
        self.last_equity = None

    def update(self, equity: float):
        equity = float(equity)

        if self.last_equity is None:
            self.last_equity = equity
            return

        if self.last_equity == 0:
            self.last_equity = equity
            return

        ret = (equity - self.last_equity) / self.last_equity
        self.returns.append(ret)
        self.last_equity = equity

        if len(self.returns) > self.window:
            self.returns.pop(0)

    def realized_vol(self) -> float:
        if len(self.returns) < 2:
            return 0.0

        mean = sum(self.returns) / len(self.returns)
        var = sum((r - mean) ** 2 for r in self.returns) / len(self.returns)
        # annualized daily vol
        return math.sqrt(var) * math.sqrt(252)

    def multiplier(self) -> float:
        vol = self.realized_vol()

        if vol <= 0:
            return 1.0

        raw = self.target_vol / vol

        if raw < self.min_multiplier:
            return self.min_multiplier

        if raw > self.max_multiplier:
            return self.max_multiplier

        return raw
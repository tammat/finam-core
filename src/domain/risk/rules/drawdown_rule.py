from domain.risk.risk_decision import RiskDecision
from domain.risk.risk_context import RiskContext


class DrawdownRule:

    def __init__(self, max_drawdown: float):
        self.max_drawdown = max_drawdown
        self._peak_equity = 0.0

    def evaluate(self, context: RiskContext) -> RiskDecision:

        equity = context.equity

        if equity > self._peak_equity:
            self._peak_equity = equity

        if self._peak_equity <= 0:
            return RiskDecision.allow()

        drawdown = (self._peak_equity - equity) / self._peak_equity

        if drawdown >= self.max_drawdown:
            return RiskDecision.deny(
                "max_drawdown_exceeded",
                rule=self.__class__.__name__,
            )

        return RiskDecision.allow()
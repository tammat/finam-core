from domain.risk.risk_decision import RiskDecision
from domain.risk.risk_context import RiskContext


class DrawdownRule:

    def __init__(self, max_drawdown: float):
        self.max_drawdown = max_drawdown
        self._peak_equity: float = 0.0

    def evaluate(self, context: RiskContext) -> RiskDecision:
        equity = context.portfolio_value

        if equity > self._peak_equity:
            self._peak_equity = equity

        if self._peak_equity == 0:
            return RiskDecision.allow()

        drawdown = (self._peak_equity - equity) / self._peak_equity

        if drawdown >= self.max_drawdown:
            return RiskDecision.reject("max_drawdown_exceeded")

        return RiskDecision.allow()

    # ---- state persistence ----

    def get_state(self):
        return {"peak_equity": self._peak_equity}

    def load_state(self, state: dict | None):
        if not state:
            return
        self._peak_equity = state.get("peak_equity", 0.0)
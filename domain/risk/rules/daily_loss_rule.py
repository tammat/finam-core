from domain.risk.risk_decision import RiskDecision
from domain.risk.risk_context import RiskContext


class DailyLossRule:

    def __init__(self, max_daily_loss: float):
        """
        max_daily_loss: доля от starting capital (например 0.05 = 5%)
        """
        self.max_daily_loss = max_daily_loss

    def evaluate(self, context: RiskContext) -> RiskDecision:

        if context.daily_realized_pnl is None:
            return RiskDecision.allow()

        if context.starting_capital == 0:
            return RiskDecision.allow()

        daily_dd = context.daily_realized_pnl / context.starting_capital

        if daily_dd <= -abs(self.max_daily_loss):
            return RiskDecision.reject("daily_loss_limit_exceeded")

        return RiskDecision.allow()
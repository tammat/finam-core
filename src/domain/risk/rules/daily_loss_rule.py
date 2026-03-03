from domain.risk.risk_decision import RiskDecision
from domain.risk.risk_context import RiskContext


class DailyLossRule:

    def __init__(self, max_daily_loss: float):
        self.max_daily_loss = abs(max_daily_loss)

    def evaluate(self, context: RiskContext) -> RiskDecision:

        if context.starting_capital <= 0:
            return RiskDecision.allow()

        daily_loss_pct = context.daily_realized_pnl / context.starting_capital

        if daily_loss_pct <= -self.max_daily_loss:
            return RiskDecision.deny(
                "daily_loss_limit_exceeded",
                rule=self.__class__.__name__,
            )

        return RiskDecision.allow()
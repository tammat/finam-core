from domain.risk.risk_decision import RiskDecision
from domain.risk.risk_context import RiskContext


class TradingEnabledRule:

    def __init__(self, enabled: bool):
        self.enabled = enabled

    def evaluate(self, context: RiskContext) -> RiskDecision:

        if not self.enabled:
            return RiskDecision.deny(
                reason="trading_disabled",
                rule=self.__class__.__name__,
            )

        return RiskDecision.allow()
from domain.risk.risk_decision import RiskDecision
from domain.risk.risk_context import RiskContext


class PortfolioHeatRule:

    def __init__(self, max_heat_pct: float):
        self.max_heat_pct = max_heat_pct

    def evaluate(self, context: RiskContext) -> RiskDecision:

        if context.portfolio_heat > self.max_heat_pct:
            return RiskDecision.deny(
                reason="portfolio_heat_exceeded",
                rule=self.__class__.__name__,
            )

        return RiskDecision.allow()
from typing import Protocol
from domain.risk.risk_context import RiskContext
from domain.risk.risk_decision import RiskDecision


class RiskRule(Protocol):
    def evaluate(self, context: RiskContext) -> RiskDecision:
        ...
from typing import Protocol
from finam_core.domain.risk.risk_context import RiskContext
from finam_core.domain.risk.risk_decision import RiskDecision


class RiskRule(Protocol):
    def evaluate(self, context: RiskContext) -> RiskDecision:
        ...
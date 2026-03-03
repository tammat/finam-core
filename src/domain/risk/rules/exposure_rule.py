from domain.risk.risk_decision import RiskDecision
from domain.risk.risk_context import RiskContext


class ExposureRule:

    def __init__(self, max_total_exposure: float, max_symbol_exposure: float):
        self.max_total_exposure = max_total_exposure
        self.max_symbol_exposure = max_symbol_exposure

    def evaluate(self, context: RiskContext) -> RiskDecision:

        if context.equity <= 0:
            return RiskDecision.deny("zero_equity", rule=self.__class__.__name__)

        new_total = context.total_exposure + context.trade_value
        if new_total > self.max_total_exposure:
            return RiskDecision.deny(
                "max_total_exposure_exceeded",
                rule=self.__class__.__name__,
            )

        new_symbol = context.current_symbol_exposure + context.trade_value
        if new_symbol > self.max_symbol_exposure:
            return RiskDecision.deny(
                "max_symbol_exposure_exceeded",
                rule=self.__class__.__name__,
            )

        return RiskDecision.allow()
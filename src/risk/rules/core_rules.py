# risk/rules/core_rules.py

from risk.risk_engine import BaseRiskRule, RiskResult, RiskContext


class DailyLossLimitRule(BaseRiskRule):

    def __init__(self, limit: float):
        self.limit = limit

    def evaluate(self, intent, context: RiskContext) -> RiskResult:
        if context.daily_pnl < -self.limit:
            return RiskResult(False, "DAILY_LOSS_LIMIT", freeze=True)
        return RiskResult(True)


class MaxDrawdownRule(BaseRiskRule):

    def __init__(self, max_dd: float):
        self.max_dd = max_dd

    def evaluate(self, intent, context: RiskContext) -> RiskResult:
        if context.drawdown_pct > self.max_dd:
            return RiskResult(False, "MAX_DRAWDOWN", freeze=True)
        return RiskResult(True)


class MaxExposureRule(BaseRiskRule):

    def __init__(self, limit: float):
        self.limit = limit

    def evaluate(self, intent, context: RiskContext) -> RiskResult:
        asset = getattr(intent, "asset", None)

        if asset and context.exposure_by_asset.get(asset, 0) > self.limit:
            return RiskResult(False, "EXPOSURE_LIMIT")

        return RiskResult(True)
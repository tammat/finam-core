from domain.risk.risk_config import RiskConfig
from domain.risk.risk_stack import RiskStack
from domain.risk.rules.exposure_rule import ExposureRule
from domain.risk.rules.drawdown_rule import DrawdownRule
from domain.risk.rules.daily_loss_rule import DailyLossRule

def build_risk_stack(config: RiskConfig | None = None) -> RiskStack:
    cfg = config or RiskConfig()

    return RiskStack(
        rules=[
            ExposureRule(...),
            DrawdownRule(max_drawdown=cfg.max_drawdown),
            DailyLossRule(max_daily_loss=cfg.max_daily_loss),
        ]
    )
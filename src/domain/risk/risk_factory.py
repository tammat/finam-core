from domain.risk.risk_stack import RiskStack
from domain.risk.risk_config import RiskConfig

from domain.risk.rules.trading_enabled_rule import TradingEnabledRule
from domain.risk.rules.exposure_rule import ExposureRule
from domain.risk.rules.drawdown_rule import DrawdownRule
from domain.risk.rules.daily_loss_rule import DailyLossRule
from domain.risk.rules.portfolio_heat_rule import PortfolioHeatRule


def build_risk_stack(config: RiskConfig | None = None) -> RiskStack:

    cfg = config or RiskConfig()

    rules = [
        TradingEnabledRule(cfg.trading_enabled),
        ExposureRule(cfg.max_total_exposure, cfg.max_symbol_exposure),
        DrawdownRule(cfg.max_drawdown),
        DailyLossRule(cfg.daily_loss_limit),
        PortfolioHeatRule(cfg.max_portfolio_heat),
    ]

    return RiskStack(rules)
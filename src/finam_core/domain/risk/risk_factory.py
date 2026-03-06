import os

from finam_core.domain.risk.risk_stack import RiskStack
from finam_core.domain.risk.risk_config import RiskConfig

from finam_core.domain.risk.rules.trading_enabled_rule import TradingEnabledRule
from finam_core.domain.risk.rules.exposure_rule import ExposureRule
from finam_core.domain.risk.rules.drawdown_rule import DrawdownRule
from finam_core.domain.risk.rules.daily_loss_rule import DailyLossRule
from finam_core.domain.risk.rules.portfolio_heat_rule import PortfolioHeatRule


def build_risk_stack(config: RiskConfig | None = None) -> RiskStack:
    cfg = config or RiskConfig()

    # env overrides config
    max_total = float(os.getenv("RISK_MAX_GROSS_EXPOSURE_PCT", str(cfg.max_total_exposure)))
    max_symbol = float(os.getenv("RISK_MAX_POSITION_PCT", str(cfg.max_symbol_exposure)))

    rules = [
        TradingEnabledRule(cfg.trading_enabled),
        ExposureRule(max_total, max_symbol),
        DrawdownRule(cfg.max_drawdown),
        DailyLossRule(cfg.daily_loss_limit),
        PortfolioHeatRule(cfg.max_portfolio_heat),
    ]

    return RiskStack(rules)

from domain.risk.pre_trade_stack import PreTradeRiskStack
from domain.risk.rules.trading_enabled_rule import TradingEnabledRule
from domain.risk.rules.daily_loss_rule import DailyLossRule
from domain.risk.rules.exposure_rule import ExposureRule
from domain.risk.rules.drawdown_rule import DrawdownRule


def build_pre_trade_stack(config):

    rules = []

    if config.trading_enabled is not None:
        rules.append(TradingEnabledRule(config.trading_enabled))

    if config.daily_loss_limit is not None:
        rules.append(DailyLossRule(config.daily_loss_limit))

    if config.max_total_exposure is not None:
        rules.append(
            ExposureRule(
                max_total_exposure=config.max_total_exposure,
                max_symbol_exposure=config.max_position_per_symbol,
                max_risk_per_trade_pct=config.max_risk_per_trade,
                allowed_symbols=config.allowed_symbols,            )
        )

    if hasattr(config, "max_drawdown") and config.max_drawdown is not None:
        rules.append(DrawdownRule(config.max_drawdown))

    return PreTradeRiskStack(rules)
import os




_PRINTED_FACTORY_DEBUG = False
def _pct_to_fraction(x: float) -> float:
    """
    Accepts either:
      - fractions: 1.5 (150%), 0.2 (20%)
      - percents: 150.0, 20.0
    Returns fraction.
    """
    x = float(x)
    # heuristic: values > 10 are almost certainly "percent"
    return x / 100.0 if x > 10.0 else x

from finam_core.domain.risk.risk_stack import RiskStack
from finam_core.domain.risk.risk_config import RiskConfig

from finam_core.domain.risk.rules.trading_enabled_rule import TradingEnabledRule
from finam_core.domain.risk.rules.exposure_rule import ExposureRule
from finam_core.domain.risk.rules.drawdown_rule import DrawdownRule
from finam_core.domain.risk.rules.daily_loss_rule import DailyLossRule
from finam_core.domain.risk.rules.portfolio_heat_rule import PortfolioHeatRule


def build_risk_stack(config: RiskConfig | None = None) -> RiskStack:
    cfg = config or RiskConfig()


    max_total_raw = float(os.getenv("RISK_MAX_GROSS_EXPOSURE_PCT", str(cfg.max_total_exposure)))
    max_symbol_raw = float(os.getenv("RISK_MAX_POSITION_PCT", str(cfg.max_symbol_exposure)))
    max_total = _pct_to_fraction(max_total_raw)
    max_symbol = _pct_to_fraction(max_symbol_raw)

    global _PRINTED_FACTORY_DEBUG
    if os.getenv("RISK_DEBUG") == "1" and not _PRINTED_FACTORY_DEBUG:
        _PRINTED_FACTORY_DEBUG = True
        print(
            "RISK_DEBUG factory "
            f"max_total_raw={max_total_raw} -> {max_total} "
            f"max_symbol_raw={max_symbol_raw} -> {max_symbol}",
            flush=True,
        )
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

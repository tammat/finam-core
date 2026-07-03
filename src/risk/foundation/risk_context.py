from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from portfolio.portfolio_state import PortfolioState
from strategy.signal import StrategySignal


@dataclass(frozen=True)
class RiskContext:
    signal: StrategySignal
    portfolio: PortfolioState
    asset_class: str
    requested_quantity: Decimal
    max_risk_per_trade: Decimal
    daily_loss_limit: Decimal
    exposure_limit: Decimal
    kill_switch_enabled: bool

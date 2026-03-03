from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class RiskContext:
    symbol: str
    trade_value: float
    portfolio_value: float
    current_symbol_exposure: float
    total_exposure: float

    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0

    daily_realized_pnl: float = 0.0
    starting_capital: float = 0.0
    equity: float = 0.0
    gross_exposure: float = 0.0
    portfolio_heat: float = 0.0
    positions: dict = None
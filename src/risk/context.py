from dataclasses import dataclass
from typing import Dict
from accounting.position_manager import Position


@dataclass
class RiskContext:
    # capital state
    cash: float
    equity: float
    realized_pnl: float
    unrealized_pnl: float

    # high-water mark & drawdown
    peak_equity: float
    drawdown: float

    # daily control
    daily_realized_pnl: float
    daily_drawdown: float

    # exposures
    gross_exposure: float
    portfolio_heat: float

    # positions snapshot
    positions: Dict[str, Position]

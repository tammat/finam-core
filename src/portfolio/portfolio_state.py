from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PortfolioState:
    equity: Decimal
    free_cash: Decimal
    gross_exposure: Decimal
    symbol_exposure: Decimal
    open_positions: int
    daily_pnl: Decimal
    daily_drawdown: Decimal

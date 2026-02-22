from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class PortfolioState:
    equity: float
    cash: float
    margin_used: float
    exposure: float
    drawdown: float
    ts: datetime


class PortfolioManager:

    def __init__(self, initial_cash: float):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.margin_used = 0.0
        self.peak_equity = initial_cash

    # ----------------------------------------------------
    # Update cash on fill
    # ----------------------------------------------------

    def apply_fill(self, side: str, qty: float, price: float, commission: float):

        trade_value = qty * price

        if side.upper() == "BUY":
            self.cash -= trade_value
        else:
            self.cash += trade_value

        self.cash -= commission

    # ----------------------------------------------------
    # Recalculate portfolio state
    # ----------------------------------------------------
    def compute_state(self, position_manager, timestamp: datetime) -> PortfolioState:

        unrealized = position_manager.total_unrealized()
        exposure = position_manager.total_exposure()

        # Realized уже отражён в cash
        equity = self.cash + unrealized

        if equity > self.peak_equity:
            self.peak_equity = equity

        drawdown = (self.peak_equity - equity)

        return PortfolioState(
            equity=equity,
            cash=self.cash,
            margin_used=self.margin_used,
            exposure=exposure,
            drawdown=drawdown,
            ts=timestamp,
        )
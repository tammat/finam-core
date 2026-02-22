from dataclasses import dataclass
from typing import Dict
from collections import defaultdict


@dataclass
class Position:
    symbol: str
    qty: float = 0.0
    avg_price: float = 0.0
    realized_pnl: float = 0.0
    market_price: float = 0.0


class PositionManager:

    def __init__(self, starting_cash: float = 0.0):
        self.cash = float(starting_cash)

        self.positions: Dict[str, Position] = defaultdict(
            lambda: Position(symbol="")
        )

        self.processed_fills = set()
        self._peak_equity = float(starting_cash)

    # --------------------------------------------------

    def apply_fill(self, fill):

        if fill.fill_id in self.processed_fills:
            return

        self.processed_fills.add(fill.fill_id)

        pos = self.positions[fill.symbol]

        signed_qty = fill.qty if fill.side == "BUY" else -fill.qty

        # Increase / open
        if pos.qty == 0 or (pos.qty > 0 and signed_qty > 0) or (pos.qty < 0 and signed_qty < 0):
            new_qty = pos.qty + signed_qty

            if new_qty != 0:
                pos.avg_price = (
                    pos.qty * pos.avg_price + signed_qty * fill.price
                ) / new_qty

            pos.qty = new_qty

        # Reduce / close
        else:
            closing = min(abs(pos.qty), abs(signed_qty))
            pnl = closing * (fill.price - pos.avg_price)

            if pos.qty < 0:
                pnl = -pnl

            pos.realized_pnl += pnl
            pos.qty += signed_qty

            if pos.qty == 0:
                pos.avg_price = 0.0

        # Cash update
        self.cash -= signed_qty * fill.price
        self.cash -= fill.commission

    # --------------------------------------------------

    def update_market_price(self, symbol: str, price: float):
        pos = self.positions[symbol]
        pos.market_price = price

    # --------------------------------------------------

    def total_equity(self):

        market_value = sum(
            p.qty * (p.market_price if p.market_price else p.avg_price)
            for p in self.positions.values()
        )

        equity = self.cash + market_value

        if equity > self._peak_equity:
            self._peak_equity = equity

        return equity

    # --------------------------------------------------

    def current_drawdown(self):

        equity = self.total_equity()

        if self._peak_equity == 0:
            return 0.0

        return (equity - self._peak_equity) / self._peak_equity

    # --------------------------------------------------

    def get_context(self):

        gross_exposure = sum(
            abs(p.qty * (p.market_price if p.market_price else p.avg_price))
            for p in self.positions.values()
        )

        equity = self.total_equity()

        return type("Context", (), {
            "cash": self.cash,
            "gross_exposure": gross_exposure,
            "equity": equity,
        })()

    # --------------------------------------------------

    def on_fill(self, fill):
        self.apply_fill(fill)
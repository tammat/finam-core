from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict


@dataclass
class Position:
    symbol: str
    qty: float = 0.0
    avg_price: float = 0.0
    realized_pnl: float = 0.0


class PositionManager:

    def __init__(self):
        self.positions = {}

    def on_fill(self, fill):
        symbol = fill.symbol
        side = fill.side
        qty = fill.qty
        price = fill.price

        pos = self.positions.get(symbol)

        if pos is None:
            pos = Position(symbol=symbol)
            self.positions[symbol] = pos

        if side == "BUY":
            new_qty = pos.qty + qty
            pos.avg_price = (
                (pos.avg_price * pos.qty + price * qty) / new_qty
                if new_qty != 0 else 0
            )
            pos.qty = new_qty

        elif side == "SELL":
            pos.realized_pnl += (price - pos.avg_price) * qty
            pos.qty -= qty

        return pos

    def total_realized(self):
        return sum(p.realized_pnl for p in self.positions.values())

    def total_unrealized(self):
        return 0.0  # пока без mark-to-market

    def total_exposure(self):
        return sum(abs(p.qty * p.avg_price) for p in self.positions.values())
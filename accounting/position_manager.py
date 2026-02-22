from typing import Dict
from dataclasses import dataclass


@dataclass
class Position:
    symbol: str
    qty: float = 0.0
    avg_price: float = 0.0
    realized_pnl: float = 0.0


class PositionManager:

    def __init__(self):
        self.positions: Dict[str, Position] = {}

    # ====================================================
    # FILL HANDLING
    # ====================================================

    def on_fill(self, fill) -> None:
        """
        Update position state after execution fill.
        """

        symbol = fill.symbol
        side = fill.side.upper()
        qty = fill.qty
        price = fill.price

        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol)

        pos = self.positions[symbol]

        signed_qty = qty if side == "BUY" else -qty

        # If same direction — adjust average price
        if pos.qty == 0 or (pos.qty > 0 and signed_qty > 0) or (pos.qty < 0 and signed_qty < 0):
            new_qty = pos.qty + signed_qty
            if new_qty != 0:
                pos.avg_price = (
                    (pos.avg_price * abs(pos.qty) + price * abs(signed_qty))
                    / abs(new_qty)
                )
            pos.qty = new_qty
        else:
            # Opposite direction → closing or flipping
            closing_qty = min(abs(pos.qty), abs(signed_qty))
            pnl = closing_qty * (price - pos.avg_price)
            if pos.qty < 0:
                pnl = -pnl

            pos.realized_pnl += pnl
            pos.qty += signed_qty

            if pos.qty == 0:
                pos.avg_price = 0.0

    # ====================================================
    # AGGREGATES
    # ====================================================

    def total_unrealized(self) -> float:
        # Unrealized not implemented without live mark price
        return 0.0

    def total_realized(self) -> float:
        return sum(p.realized_pnl for p in self.positions.values())

    def total_exposure(self) -> float:
        return sum(abs(p.qty) * p.avg_price for p in self.positions.values())
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class Position:
    symbol: str
    qty: float = 0.0
    avg_price: float = 0.0
    realized_pnl: float = 0.0
    mark_price: float = 0.0

    @property
    def notional(self) -> float:
        return abs(self.qty) * (self.mark_price if self.mark_price else self.avg_price)


class PositionManager:
    """
    Minimal, stable PositionManager for live/paper pipeline.

    Contract used across repo:
      - apply_fill(symbol, side, qty, price) -> realized_pnl_delta (float)
      - get_position_qty(symbol) -> float
      - on_price(symbol, price) -> None
      - positions: Dict[str, Position]
    """

    def __init__(self):
        self.positions: Dict[str, Position] = {}

    def get_position(self, symbol: str) -> Position:
        pos = self.positions.get(symbol)
        if pos is None:
            pos = Position(symbol=symbol)
            self.positions[symbol] = pos
        return pos

    def get_position_qty(self, symbol: str) -> float:
        pos = self.positions.get(symbol)
        if pos is not None:
            return float(pos.qty)
        # fallback: sometimes keys are stored without MIC
        short = symbol.split("@", 1)[0]
        pos = self.positions.get(short)
        return float(pos.qty) if pos is not None else 0.0

    def on_price(self, symbol: str, price: float) -> None:
        pos = self.get_position(symbol)
        pos.mark_price = float(price)

    def apply_fill(self, symbol: str, side: str, qty: float, price: float) -> float:
        side_u = str(side).upper()
        qty = float(qty)
        if qty <= 0:
            raise ValueError("qty must be > 0")
        price = float(price)

        pos = self.get_position(symbol)
        realized_delta = 0.0

        if side_u == "BUY":
            # If we are short, BUY closes short first.
            if pos.qty < 0:
                cover = min(qty, abs(pos.qty))
                realized_delta += (pos.avg_price - price) * cover  # short pnl
                pos.qty += cover  # pos.qty increases toward 0
                qty -= cover
                if pos.qty == 0:
                    pos.avg_price = 0.0
            if qty > 0:
                # increase long
                new_qty = pos.qty + qty
                pos.avg_price = ((pos.avg_price * pos.qty) + (price * qty)) / new_qty if new_qty != 0 else 0.0
                pos.qty = new_qty

        elif side_u == "SELL":
            # If we are long, SELL closes long first.
            if pos.qty > 0:
                close = min(qty, pos.qty)
                realized_delta += (price - pos.avg_price) * close  # long pnl
                pos.qty -= close
                qty -= close
                if pos.qty == 0:
                    pos.avg_price = 0.0
            if qty > 0:
                # increase short
                new_qty = abs(pos.qty) + qty  # pos.qty is 0 or negative here
                # avg_price for short = weighted entry price
                entry_qty = qty
                existing_qty = abs(pos.qty)
                pos.avg_price = ((pos.avg_price * existing_qty) + (price * entry_qty)) / (existing_qty + entry_qty) if (existing_qty + entry_qty) != 0 else 0.0
                pos.qty = -(existing_qty + entry_qty)

        else:
            raise ValueError(f"unknown side: {side}")

        pos.realized_pnl += realized_delta
        pos.mark_price = price  # last trade as mark fallback
        return realized_delta

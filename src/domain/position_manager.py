from dataclasses import dataclass


@dataclass
class Position:
    symbol: str
    qty: float = 0.0
    avg_price: float = 0.0
    realized_pnl: float = 0.0


class PositionManager:
    """
    Responsible ONLY for position math.
    No accounting.
    No equity.
    """

    def __init__(self):
        self.positions = {}

    def apply_fill(self, symbol, side, qty, price):
        pos = self.positions.get(symbol)

        if pos is None:
            pos = Position(symbol=symbol)
            self.positions[symbol] = pos

        signed_qty = qty if side == "BUY" else -qty

        # --- Strict sign invariant ---
        if pos.qty != 0 and (pos.qty > 0) != (signed_qty > 0):
            # opposite direction → closing
            if abs(signed_qty) > abs(pos.qty):
                raise RuntimeError("POSITION_SIGN_FLIP_WITHOUT_CLOSE")

        # --- Realized calculation ---
        realized = 0.0

        if pos.qty == 0:
            pos.avg_price = price
            pos.qty = signed_qty
        elif (pos.qty > 0 and signed_qty > 0) or (pos.qty < 0 and signed_qty < 0):
            # same direction → averaging
            total_value = pos.qty * pos.avg_price + signed_qty * price
            pos.qty += signed_qty
            pos.avg_price = total_value / pos.qty
        else:
            # closing logic
            closing_qty = min(abs(pos.qty), abs(signed_qty))
            realized = closing_qty * (price - pos.avg_price) * (1 if pos.qty > 0 else -1)

            pos.qty += signed_qty

            if pos.qty == 0:
                pos.avg_price = 0.0

        pos.realized_pnl += realized

        return realized
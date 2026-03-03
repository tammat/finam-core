class PositionCap:
    def __init__(self, max_position_pct: float):
        self.max_position_pct = max_position_pct

    def apply(self, qty: float, price: float, equity: float) -> float:
        if not self.max_position_pct:
            return qty

        max_value = equity * self.max_position_pct
        max_qty = max_value / price

        return min(qty, max_qty)
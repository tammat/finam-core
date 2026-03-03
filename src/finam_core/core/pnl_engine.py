class PnLEngine:

    def __init__(self):
        self.realized = 0.0

    def mark_to_market(self, position_qty, avg_price, last_price):
        unrealized = (last_price - avg_price) * position_qty
        return unrealized
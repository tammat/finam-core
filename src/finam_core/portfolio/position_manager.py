class PositionManager:

    def __init__(self):

        self.positions = {}

        self.realized_pnl = 0.0

    # ------------------------------------------------

    def update_fill(self, symbol, side, qty, price):

        pos = self.positions.get(symbol)

        if pos is None:

            self.positions[symbol] = {
                "qty": qty if side == "BUY" else -qty,
                "avg_price": price
            }

            return

        current_qty = pos["qty"]
        avg_price = pos["avg_price"]

        if side == "BUY":
            new_qty = current_qty + qty
        else:
            new_qty = current_qty - qty

        # закрытие позиции

        if current_qty * new_qty < 0:

            realized = (price - avg_price) * current_qty

            self.realized_pnl += realized

            pos["qty"] = new_qty
            pos["avg_price"] = price

            return

        # добавление

        if side == "BUY":

            total_cost = avg_price * current_qty + price * qty
            pos["qty"] = new_qty
            pos["avg_price"] = total_cost / new_qty

        else:

            pos["qty"] = new_qty
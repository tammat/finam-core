class PositionManager:

    def __init__(self):
        self.qty = 0.0
        self.avg_price = 0.0
        self.realized = 0.0

    def on_fill(self, side: str, qty: float, price: float):

        if side == "BUY":
            if self.qty >= 0:
                # увеличение лонга
                total_cost = self.avg_price * self.qty + price * qty
                self.qty += qty
                self.avg_price = total_cost / self.qty
            else:
                # закрытие шорта
                closing_qty = min(qty, abs(self.qty))
                self.realized += (self.avg_price - price) * closing_qty
                self.qty += qty
                if self.qty > 0:
                    # flip в лонг
                    self.avg_price = price
                elif self.qty == 0:
                    self.avg_price = 0.0

        elif side == "SELL":
            if self.qty <= 0:
                # увеличение шорта
                total_cost = self.avg_price * abs(self.qty) + price * qty
                self.qty -= qty
                self.avg_price = total_cost / abs(self.qty)
            else:
                # закрытие лонга
                closing_qty = min(qty, self.qty)
                self.realized += (price - self.avg_price) * closing_qty
                self.qty -= qty
                if self.qty < 0:
                    # flip в шорт
                    self.avg_price = price
                elif self.qty == 0:
                    self.avg_price = 0.0

    def unrealized(self, last_price: float):
        return (last_price - self.avg_price) * self.qty

    def snapshot(self, last_price: float):
        return {
            "qty": self.qty,
            "avg_price": self.avg_price,
            "realized": self.realized,
            "unrealized": self.unrealized(last_price),
        }
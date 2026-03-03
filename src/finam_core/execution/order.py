from enum import Enum


class OrderStatus(Enum):
    NEW = "NEW"
    ACCEPTED = "ACCEPTED"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"


class Order:
    def __init__(self, order_id: str, symbol: str, side: str, qty: float, price: float):
        self.id = order_id
        self.symbol = symbol
        self.side = side
        self.qty = float(qty)
        self.price = float(price)

        self.filled_qty = 0.0
        self.status = OrderStatus.NEW

    def remaining_qty(self) -> float:
        return self.qty - self.filled_qty
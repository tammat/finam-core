from execution.order import Order, OrderStatus
from execution.order_events import FillEvent


class OrderManager:
    def __init__(self):
        self.orders = {}
        self.processed_fill_ids = set()

    def create_order(self, order_id: str, symbol: str, side: str, qty: float, price: float) -> Order:
        if order_id in self.orders:
            raise RuntimeError("ORDER_ALREADY_EXISTS")

        order = Order(order_id, symbol, side, qty, price)
        self.orders[order_id] = order
        return order

    def accept_order(self, order_id: str):
        order = self._get(order_id)
        self._transition(order, OrderStatus.ACCEPTED)

    def reject_order(self, order_id: str):
        order = self._get(order_id)
        self._transition(order, OrderStatus.REJECTED)

    def cancel_order(self, order_id: str):
        order = self._get(order_id)
        if order.status not in (OrderStatus.ACCEPTED, OrderStatus.PARTIAL):
            raise RuntimeError("INVALID_STATE_TRANSITION")
        order.status = OrderStatus.CANCELED

    def on_fill(self, fill: FillEvent) -> Order:
        if fill.fill_id in self.processed_fill_ids:
            raise RuntimeError("DUPLICATE_FILL")

        order = self._get(fill.order_id)

        if order.status not in (OrderStatus.ACCEPTED, OrderStatus.PARTIAL):
            raise RuntimeError("INVALID_STATE_TRANSITION")

        if fill.qty > order.remaining_qty():
            raise RuntimeError("OVERFILL")

        order.filled_qty += fill.qty

        if order.filled_qty == order.qty:
            order.status = OrderStatus.FILLED
        else:
            order.status = OrderStatus.PARTIAL

        self.processed_fill_ids.add(fill.fill_id)
        return order

    def _get(self, order_id: str) -> Order:
        if order_id not in self.orders:
            raise RuntimeError("ORDER_NOT_FOUND")
        return self.orders[order_id]

    def _transition(self, order: Order, new_status: OrderStatus):
        if order.status == OrderStatus.NEW and new_status in (OrderStatus.ACCEPTED, OrderStatus.REJECTED):
            order.status = new_status
            return
        raise RuntimeError("INVALID_STATE_TRANSITION")
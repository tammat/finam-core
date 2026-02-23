class FillEvent:
    def __init__(self, fill_id: str, order_id: str, qty: float):
        if not fill_id:
            raise RuntimeError("FILL_ID_REQUIRED")
        if qty <= 0:
            raise RuntimeError("INVALID_FILL_QTY")

        self.fill_id = fill_id
        self.order_id = order_id
        self.qty = float(qty)
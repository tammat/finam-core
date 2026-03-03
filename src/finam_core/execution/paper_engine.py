class PaperExecutionEngine:

    def __init__(self, slippage_coef: float = 0.25):
        self.slippage_coef = slippage_coef

    def execute(self, intent, market_state):
        bid = market_state["bid"]
        ask = market_state["ask"]
        spread = max(ask - bid, 0)

        if intent.side == "BUY":
            fill_price = ask + spread * self.slippage_coef
            qty = intent.quantity
        else:
            fill_price = bid - spread * self.slippage_coef
            qty = -intent.quantity

        return type("Fill", (), {
            "symbol": intent.symbol,
            "qty": qty,
            "price": fill_price,
            "commission": 0.0,
            "fill_id": f"paper_{market_state['timestamp']}"
        })
# src/finam_core/strategy/simple_reactive.py

class SimpleReactiveStrategy:
    def __init__(self):
        self.last_price = None

    def on_quote(self, st):
        price = st.get("last")
        if price is None:
            return None

        if self.last_price is None:
            self.last_price = price
            return None

        # примитив: движение вверх → BUY
        if price > self.last_price:
            self.last_price = price
            return {"symbol": st["symbol"], "side": "BUY", "qty": 1.0}

        self.last_price = price
        return None
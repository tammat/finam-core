# src/finam_core/strategy/simple_reactive.py

import os


class SimpleReactiveStrategy:
    def __init__(self):
        self.last_price = None
        self.sent = False

    def on_quote(self, st):
        if self.sent:
            return None

        # Русский коммент: тестовый режим для проверки SELL/BUY pipeline без изменения основной логики стратегии.
        force_side = (os.getenv("FORCE_SIDE") or "").strip().upper()

        price = st.get("last")
        if price is None:
            return None

        if self.last_price is None:
            self.last_price = price
            if force_side in ("BUY", "SELL"):
                self.sent = True
                return {"symbol": st["symbol"], "side": force_side, "qty": 1.0, "reason": f"forced_{force_side.lower()}_test"}
            return None

        if force_side in ("BUY", "SELL"):
            self.last_price = price
            self.sent = True
            return {"symbol": st["symbol"], "side": force_side, "qty": 1.0, "reason": f"forced_{force_side.lower()}_test"}

        # примитив: движение вверх → BUY
        if price > self.last_price:
            self.last_price = price
            self.sent = True
            return {"symbol": st["symbol"], "side": "BUY", "qty": 1.0, "reason": "price_up"}

        # примитив: движение вниз → SELL
        if price < self.last_price:
            self.last_price = price
            self.sent = True
            return {"symbol": st["symbol"], "side": "SELL", "qty": 1.0, "reason": "price_down"}

        self.last_price = price
        return None

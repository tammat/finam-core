# src/finam_core/strategy/once_buy.py
# Русский коммент: простая стратегия — один BUY на первом валидном тике.

class OnceBuyStrategy:
    def __init__(self, symbol: str, qty: float = 1.0):
        self.symbol = symbol
        self.qty = float(qty)
        self.sent = False

    def on_quote(self, state: dict):
        sym = state.get("symbol")
        last = state.get("last")

        if not self.sent:
            print(f"STRATEGY waiting first quote: {sym} last={last}", flush=True)

        if self.sent or sym != self.symbol or last is None:
            return None

        self.sent = True
        print("STRATEGY EMIT INTENT", flush=True)
        return {"symbol": sym, "side": "BUY", "qty": self.qty}
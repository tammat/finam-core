# src/finam_core/strategy/vwap_bands_mr.py

class VWAPBandsMRStrategy:
    """
    Mean reversion от VWAP:
    - цена ниже нижней полосы → BUY
    - выше верхней → SELL (потом добавим)
    """

    def __init__(self, window=150, k=1.5, stop_pct=0.004, take_pct=0.0):
        self.window = window
        self.k = k
        self.prices = []

    def on_quote(self, st):
        price = st.get("last")
        if price is None:
            return None

        self.prices.append(price)
        if len(self.prices) < self.window:
            return None

        # ограничиваем окно
        if len(self.prices) > self.window:
            self.prices.pop(0)

        # VWAP ≈ среднее (упрощение для live)
        mean = sum(self.prices) / len(self.prices)

        # std
        variance = sum((p - mean) ** 2 for p in self.prices) / len(self.prices)
        std = variance ** 0.5

        lower = mean - self.k * std
        upper = mean + self.k * std

        # BUY сигнал
        if price < lower:
            return {
                "symbol": st["symbol"],
                "side": "BUY",
                "qty": 1.0,
            }

        # SELL пока не делаем (чтобы не ломать пайплайн)
        return None

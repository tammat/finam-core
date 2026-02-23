class SizingEngine:
    """
    Institutional Sizing Engine v2
    Supports:
        - fixed %
        - volatility (ATR-based)
    """

    def __init__(self, risk_per_trade=0.01, mode="fixed", atr_multiplier=1.0):
        self.risk_per_trade = risk_per_trade
        self.mode = mode
        self.atr_multiplier = atr_multiplier

    def size(self, signal, context):

        equity = context.equity
        price = signal.price

        if equity <= 0 or price <= 0:
            return signal

        capital_at_risk = equity * self.risk_per_trade

        # -------------------------------
        # Fixed mode
        # -------------------------------
        if self.mode == "fixed":
            qty = capital_at_risk / price

        # -------------------------------
        # Volatility mode
        # -------------------------------
        elif self.mode == "volatility":

            atr = getattr(signal, "atr", None)

            if atr is None or atr <= 0:
                # fallback
                qty = capital_at_risk / price
            else:
                stop_distance = atr * self.atr_multiplier
                qty = capital_at_risk / stop_distance

        else:
            qty = capital_at_risk / price

        signal.qty = float(qty)
        return signal
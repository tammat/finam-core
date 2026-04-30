from __future__ import annotations

class MeanReversionStrategy:

    def on_quote(self, st: dict):

        price = st.get("last")
        atr = st.get("atr")

        if price is None or atr is None:
            return None

        mid = st.get("ema_slow") or price
        deviation = price - mid

        # LONG
        if deviation < -atr * 0.5:
            return {
                "symbol": st["symbol"],
                "side": "BUY",
                "qty": 1.0,
                "reason": "mean_reversion_long",
                "price": price,
                "confidence": 0.6,
                "source": "MeanReversionStrategy",
            }

        # SHORT
        if deviation > atr * 0.5:
            return {
                "symbol": st["symbol"],
                "side": "SELL",
                "qty": 1.0,
                "reason": "mean_reversion_short",
                "price": price,
                "confidence": 0.6,
                "source": "MeanReversionStrategy",
            }

        return None
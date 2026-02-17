import random


class SlippageModel:
    """
    Institutional slippage model.
    Depends on:
    - volatility proxy
    - order size
    - side
    """

    def __init__(self, base_spread_bps=5):
        self.base_spread_bps = base_spread_bps  # 5 bps default

    def apply(self, base_price, quantity, side):
        """
        base_price: mid price
        quantity: order size
        side: BUY / SELL
        """

        # 1️⃣ Base spread component
        spread_component = base_price * (self.base_spread_bps / 10_000)

        # 2️⃣ Size impact (simple nonlinear)
        impact_component = base_price * 0.0001 * abs(quantity)

        # 3️⃣ Random micro-noise
        noise = base_price * random.uniform(-0.00005, 0.00005)

        total_slippage = spread_component + impact_component + noise

        if side == "BUY":
            return base_price + total_slippage
        else:
            return base_price - total_slippage
from domain.regime.regime_detector import RegimeState


class VolatilityTargetSizer:
    """
    Position size = base_qty * (target_vol / realized_vol)
    Deterministic. No side effects.
    """

    def __init__(
        self,
        target_vol: float,
        min_multiplier: float = 0.3,
        max_multiplier: float = 2.0,
        epsilon: float = 1e-8,
    ):
        self.target_vol = float(target_vol)
        self.min_multiplier = float(min_multiplier)
        self.max_multiplier = float(max_multiplier)
        self.epsilon = epsilon

    def apply(self, intent, regime: RegimeState, event=None, portfolio=None):

        if regime.volatility <= self.epsilon:
            return intent

        multiplier = self.target_vol / regime.volatility

        # clamp multiplier
        multiplier = max(self.min_multiplier, multiplier)
        multiplier = min(self.max_multiplier, multiplier)

        # поддержка qty / quantity
        if hasattr(intent, "quantity"):
            new_qty = intent.quantity * multiplier
            return intent.__class__(
                symbol=intent.symbol,
                side=intent.side,
                quantity=new_qty,
                confidence=getattr(intent, "confidence", 1.0),
                metadata=getattr(intent, "metadata", None),
            )

        if hasattr(intent, "qty"):
            intent.qty = intent.qty * multiplier
            return intent

        return intent
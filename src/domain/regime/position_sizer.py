# domain/regime/position_sizer.py

from domain.regime.regime_detector import VolatilityRegime


class RegimePositionSizer:
    """
    Scales position size based on volatility regime.
    Deterministic. No side effects.
    """

    def __init__(
        self,
        low_multiplier: float = 1.2,
        normal_multiplier: float = 1.0,
        high_multiplier: float = 0.5,
    ):
        self.low_multiplier = low_multiplier
        self.normal_multiplier = normal_multiplier
        self.high_multiplier = high_multiplier

    def scale(self, base_qty: float, regime) -> float:

        if regime.regime == VolatilityRegime.LOW:
            multiplier = self.low_multiplier
        elif regime.regime == VolatilityRegime.HIGH:
            multiplier = self.high_multiplier
        else:
            multiplier = self.normal_multiplier

        return base_qty * multiplier
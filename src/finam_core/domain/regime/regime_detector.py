# domain/regime/regime_detector.py

from dataclasses import dataclass
from enum import Enum
import numpy as np


class VolatilityRegime(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass(frozen=True)
class RegimeState:
    regime: VolatilityRegime
    volatility: float


class RegimeDetector:
    """
    Pure deterministic volatility regime detector.
    """

    def __init__(
        self,
        window: int = 10,
        low_threshold: float = 0.5,
        high_threshold: float = 2.0,
    ):
        self.window = window
        self.low_threshold = low_threshold
        self.high_threshold = high_threshold

    def detect(self, prices: list[float]) -> RegimeState:

        if len(prices) < self.window:
            return RegimeState(VolatilityRegime.NORMAL, 0.0)

        returns = np.diff(prices[-self.window:])
        vol = float(np.std(returns))

        if vol < self.low_threshold:
            regime = VolatilityRegime.LOW
        elif vol > self.high_threshold:
            regime = VolatilityRegime.HIGH
        else:
            regime = VolatilityRegime.NORMAL

        return RegimeState(regime, vol)
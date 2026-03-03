# risk/position_sizer.py

from dataclasses import dataclass
from typing import Optional


@dataclass
class SizingResult:
    size: float
    reason: Optional[str] = None


class PositionSizer:

    def __init__(self, max_risk_per_trade: float = 0.01):
        """
        max_risk_per_trade — доля капитала (например 0.01 = 1%)
        """
        self.max_risk_per_trade = max_risk_per_trade

    def size(self, intent, context) -> SizingResult:
        """
        Простая risk-based sizing модель.
        """

        if context.equity <= 0:
            return SizingResult(0, "NO_EQUITY")

        risk_capital = context.equity * self.max_risk_per_trade

        # Если у intent есть stop_distance — используем risk-based sizing
        stop_distance = getattr(intent, "stop_distance", None)

        if stop_distance and stop_distance > 0:
            size = risk_capital / stop_distance
        else:
            # fallback: фиксированная доля
            size = risk_capital / max(intent.price, 1)

        return SizingResult(size=size)
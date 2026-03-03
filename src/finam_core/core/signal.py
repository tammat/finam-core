# src/core/signal.py
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class SignalIntent:
    """
    Абстрактное намерение стратегии.
    НЕ является ордером.
    """

    symbol: str
    direction: int          # 1 = LONG, -1 = SHORT
    strength: float = 1.0   # сила сигнала (для future weighting)
    price: float | None = None
    timestamp: Any = None
    features: Dict[str, Any] = field(default_factory=dict)

    def is_long(self) -> bool:
        return self.direction > 0

    def is_short(self) -> bool:
        return self.direction < 0
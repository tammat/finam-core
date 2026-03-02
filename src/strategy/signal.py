# strategy/signal.py

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class Signal:
    symbol: str                 # Тикер / инструмент
    side: str                   # "BUY" | "SELL"
    quantity: float             # Количество
    confidence: float = 1.0     # Уверенность (на будущее для ансамблей)
    metadata: Dict[str, Any] | None = None  # Любые доп. поля (фичи, причины и т.д.)
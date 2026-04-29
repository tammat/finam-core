# src/finam_core/signals/signal_intent.py

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class SignalIntent:
    """
    Русский коммент: единый формат торгового сигнала до RiskEngine.
    Strategy не отправляет заявки напрямую.
    """
    symbol: str
    side: str
    qty: float
    source: str
    confidence: float = 1.0
    reason: str = ""
    features: dict[str, Any] = field(default_factory=dict)
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side.upper(),
            "qty": float(self.qty),
            "source": self.source,
            "confidence": float(self.confidence),
            "reason": self.reason,
            "features": self.features,
            "ts": self.ts,
        }

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SignalIntent:
    """
    Русский комментарий:
    Canonical SignalIntent v2.

    Единый контракт:
    strategy -> signal -> gates -> risk -> execution -> analytics.
    """

    symbol: str
    side: str
    strategy: str = "UNKNOWN_STRATEGY"

    qty: float = 1.0
    intent_type: str = "ENTRY"

    signal_id: str | None = None
    continuous_symbol: str | None = None

    entry_price: float | None = None
    stop_price: float | None = None
    take_profit: float | None = None

    confidence: float = 1.0
    timeframe: str = "LIVE"
    horizon: str = "INTRADAY"
    regime: str | None = None

    source: str = "strategy"
    reason: str = ""

    features: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    created_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        self.symbol = str(self.symbol)
        self.side = str(self.side).upper()
        self.strategy = str(self.strategy)
        self.intent_type = str(self.intent_type).upper()

        if self.signal_id is None:
            self.signal_id = f"sig-{self.strategy}-{self.symbol}-{int(self.created_at * 1000)}"

        if self.continuous_symbol is None:
            try:
                from finam_core.contracts.runtime_symbol_mapper import RuntimeSymbolMapper
                self.continuous_symbol = RuntimeSymbolMapper.runtime_symbol(self.symbol)
            except Exception:
                self.continuous_symbol = self.symbol

    @property
    def price(self) -> float | None:
        """Русский комментарий: backward-compatible alias для старого pipeline."""
        return self.entry_price

    def to_dict(self) -> dict[str, Any]:
        """Русский комментарий: совместимость со старым dict-based pipeline."""
        features = dict(self.features or {})

        if self.entry_price is not None:
            features.setdefault("entry", self.entry_price)
        if self.stop_price is not None:
            features.setdefault("stop", self.stop_price)
        if self.take_profit is not None:
            features.setdefault("take", self.take_profit)

        features.setdefault("strategy", self.strategy)
        features.setdefault("continuous_symbol", self.continuous_symbol)
        features.setdefault("regime", self.regime)

        return {
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "continuous_symbol": self.continuous_symbol,
            "side": self.side,
            "qty": float(self.qty),
            "price": self.entry_price,
            "entry_price": self.entry_price,
            "stop_price": self.stop_price,
            "take_profit": self.take_profit,
            "strategy": self.strategy,
            "intent_type": self.intent_type,
            "confidence": float(self.confidence),
            "timeframe": self.timeframe,
            "horizon": self.horizon,
            "regime": self.regime,
            "source": self.source,
            "reason": self.reason,
            "features": features,
            "metadata": dict(self.metadata or {}),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SignalIntent":
        """Русский комментарий: адаптер для старых dict-intent стратегий."""
        features = dict(data.get("features") or {})

        return cls(
            signal_id=data.get("signal_id"),
            symbol=str(data.get("symbol")),
            continuous_symbol=data.get("continuous_symbol"),
            side=str(data.get("side")),
            qty=float(data.get("qty", 1.0) or 1.0),
            entry_price=data.get("entry_price") or data.get("price") or features.get("entry"),
            stop_price=data.get("stop_price") or data.get("stop") or features.get("stop"),
            take_profit=data.get("take_profit") or data.get("take") or features.get("take"),
            strategy=str(data.get("strategy") or features.get("strategy") or "UNKNOWN_STRATEGY"),
            intent_type=str(data.get("intent_type", "ENTRY")),
            confidence=float(data.get("confidence", data.get("score", 1.0)) or 1.0),
            timeframe=str(data.get("timeframe", "LIVE")),
            horizon=str(data.get("horizon", "INTRADAY")),
            regime=data.get("regime") or features.get("regime"),
            source=str(data.get("source", "strategy")),
            reason=str(data.get("reason", "")),
            features=features,
            metadata=dict(data.get("metadata") or {}),
        )

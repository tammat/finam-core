# src/finam_core/signals/signal_router.py

from __future__ import annotations

import os
from dataclasses import dataclass

from finam_core.signals.signal_intent import SignalIntent


@dataclass
class RoutedSignal:
    allowed: bool
    reason: str
    intent: SignalIntent | None = None


class SignalRouter:
    """
    Русский коммент: минимальный SignalRouter.
    Нормализует и фильтрует сигналы до risk-stack.
    """

    def __init__(self):
        self.min_confidence = float(os.getenv("SIGNAL_MIN_CONFIDENCE", "0.0"))
        self._last_by_symbol: dict[str, str] = {}

    def route(self, intent: SignalIntent | dict | None) -> RoutedSignal:
        if intent is None:
            return RoutedSignal(False, "no_signal", None)

        if isinstance(intent, dict):
            intent = SignalIntent(
                symbol=intent["symbol"],
                side=str(intent["side"]).upper(),
                qty=float(intent.get("qty", 1.0)),
                source=str(intent.get("source", "legacy_strategy")),
                confidence=float(intent.get("confidence", 1.0)),
                reason=str(intent.get("reason", "")),
                features=dict(intent.get("features", {})),
            )

        if intent.side.upper() not in ("BUY", "SELL"):
            return RoutedSignal(False, "invalid_side", intent)

        if intent.qty <= 0:
            return RoutedSignal(False, "invalid_qty", intent)

        if intent.confidence < self.min_confidence:
            return RoutedSignal(False, "low_confidence", intent)

        key = f"{intent.symbol}:{intent.side.upper()}:{intent.reason}"
        if self._last_by_symbol.get(intent.symbol) == key:
            return RoutedSignal(False, "duplicate_signal", intent)

        self._last_by_symbol[intent.symbol] = key
        return RoutedSignal(True, "ok", intent)

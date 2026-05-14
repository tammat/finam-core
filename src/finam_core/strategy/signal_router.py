from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finam_core.strategy.quote_signal_processor import QuoteSignalInput


@dataclass(frozen=True)
class SignalRouteInput:
    """Русский комментарий: входной DTO для маршрутизации quote → raw_intent."""
    symbol: str
    state: dict[str, Any]


@dataclass(frozen=True)
class BlockedSignalIntent:
    """Русский комментарий: безопасный intent-заглушка, если стратегия не дала сигнал."""
    allowed: bool = False
    side: str | None = None
    qty: float = 0.0
    reason: str = "no_signal"


class SignalRouter:
    """
    Русский комментарий:
    Signal Routing Layer.

    Гарантия контракта:
    route() никогда не возвращает None.
    """

    def __init__(self, quote_signal_processor) -> None:
        self.quote_signal_processor = quote_signal_processor

    def route(self, data):
        """Русский комментарий: маршрутизирует сигнал через QuoteSignalProcessor."""
        if isinstance(data, dict):
            symbol = data.get("symbol")
            state = data.get("state") or data
        else:
            symbol = getattr(data, "symbol", None)
            state = getattr(data, "state", None)

        if not symbol:
            return BlockedSignalIntent(reason="missing_symbol")

        result = self.quote_signal_processor.process(
            QuoteSignalInput(
                symbol=symbol,
                state=state or {},
            )
        )

        if result is None:
            return BlockedSignalIntent(reason="no_signal")

        return result

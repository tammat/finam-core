from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NormalizedQuote:
    """Русский комментарий: единый внутренний формат quote-события."""
    raw_event: Any
    symbol: str | None
    price: float | None
    bid: float | None = None
    ask: float | None = None
    atr: float | None = None
    source: str = "unknown"


class QuoteNormalizer:
    """Русский комментарий: изолирует брокерский/raw payload от pipeline orchestration."""

    @staticmethod
    def _get(event: Any, key: str, default: Any = None) -> Any:
        if isinstance(event, dict):
            return event.get(key, default)
        return getattr(event, key, default)

    @classmethod
    def normalize(cls, event: Any) -> NormalizedQuote:
        symbol = cls._get(event, "symbol")
        price = (
            cls._get(event, "price")
            or cls._get(event, "last")
            or cls._get(event, "last_price")
            or cls._get(event, "close")
        )

        bid = cls._get(event, "bid")
        ask = cls._get(event, "ask")
        atr = cls._get(event, "atr")
        source = cls._get(event, "source", "unknown")

        return NormalizedQuote(
            raw_event=event,
            symbol=str(symbol) if symbol is not None else None,
            price=float(price) if price is not None else None,
            bid=float(bid) if bid is not None else None,
            ask=float(ask) if ask is not None else None,
            atr=float(atr) if atr is not None else None,
            source=str(source),
        )

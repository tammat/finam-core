from __future__ import annotations

from typing import Any


class ClosedTradeAttributionService:
    """Русский комментарий: связывает fill с signal_fills по metadata из payload."""

    def __init__(self, signal_repository: Any | None = None) -> None:
        self.signal_repository = signal_repository

    def link_fill_from_payload(self, fill: Any) -> bool:
        if self.signal_repository is None:
            return False

        payload = getattr(fill, "payload", None)
        if not isinstance(payload, dict):
            payload = {}

        signal_id = (
            getattr(fill, "signal_id", None)
            or payload.get("signal_id")
        )

        fill_id = (
            getattr(fill, "fill_id", None)
            or getattr(fill, "trade_id", None)
            or payload.get("trade_id")
        )

        if not signal_id or not fill_id:
            return False

        self.signal_repository.link_fill(
            signal_id=str(signal_id),
            fill_id=str(fill_id),
            symbol=str(getattr(fill, "symbol", payload.get("symbol", ""))),
            side=str(getattr(fill, "side", payload.get("side", ""))),
            qty=float(getattr(fill, "qty", payload.get("qty", 0.0)) or 0.0),
            price=float(getattr(fill, "price", payload.get("price", 0.0)) or 0.0),
        )
        self.signal_repository.mark_filled(str(signal_id))
        return True

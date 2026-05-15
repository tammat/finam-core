from __future__ import annotations

from typing import Any


class FillPersistenceService:
    """Русский комментарий: единая запись fill/trade/signal_fills для PAPER/REAL/REPLAY."""

    def __init__(
        self,
        pg_logger: Any | None = None,
        attribution_service: Any | None = None,
    ) -> None:
        self.pg_logger = pg_logger
        self.attribution_service = attribution_service

    def persist_fill(self, fill: Any, execution_type: str = "paper") -> dict:
        """Русский комментарий: пишет fill в БД и связывает fill с signal_id при наличии metadata."""
        result = {
            "fill_logged": False,
            "signal_linked": False,
            "fill_id": getattr(fill, "fill_id", None),
            "signal_id": getattr(fill, "signal_id", None),
        }

        if self.pg_logger is not None:
            self.pg_logger.log_fill(
                symbol=getattr(fill, "symbol", None),
                side=getattr(fill, "side", None),
                qty=float(getattr(fill, "qty", 0.0) or 0.0),
                price=float(getattr(fill, "price", 0.0) or 0.0),
                trade_id=getattr(fill, "fill_id", None),
                execution_type=execution_type,
                commission=float(getattr(fill, "commission", 0.0) or 0.0),
                payload=getattr(fill, "payload", None),
            )
            result["fill_logged"] = True

        if self.attribution_service is not None:
            result["signal_linked"] = bool(
                self.attribution_service.link_fill_from_payload(fill)
            )

        return result

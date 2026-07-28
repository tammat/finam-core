from __future__ import annotations

from typing import Any
import os


class FillPersistenceService:
    """Русский комментарий: единая запись fill/trade/signal_fills для PAPER/REAL/REPLAY."""

    def __init__(
        self,
        pg_logger: Any | None = None,
        attribution_service: Any | None = None,
    ) -> None:
        self.pg_logger = pg_logger
        self.attribution_service = attribution_service

    def persist_fill(self, fill: Any, execution_type: str = "paper", payload: dict | None = None) -> dict:
        """Русский комментарий: пишет fill в БД и связывает fill с signal_id при наличии metadata."""
        result = {
            "fill_logged": False,
            "signal_linked": False,
            "fill_id": getattr(fill, "fill_id", None),
            "signal_id": (payload or {}).get("signal_id") or getattr(fill, "signal_id", None),
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
                payload=payload if isinstance(payload, dict) else getattr(fill, "payload", None),
            )
            result["fill_logged"] = True

        if self.attribution_service is not None:
            result["signal_linked"] = bool(
                self.attribution_service.link_fill_from_payload(fill)
            )

        # Русский комментарий: SIGNAL_FILL_LINKAGE_PERSISTENCE_V1.
        # Если attribution_service не связал fill, но payload содержит signal_id,
        # сохраняем связь напрямую в signal_fills.
        if not result["signal_linked"]:
            result["signal_linked"] = bool(
                self._persist_signal_fill_linkage_v1(fill=fill, payload=payload)
            )

        # Любой успешно связанный fill завершает lifecycle исходного сигнала.
        # Повторный UPDATE безопасен и закрывает fallback-путь прямой записи связи.
        if result["signal_linked"]:
            signal_id = (
                (payload or {}).get("signal_id")
                or (payload or {}).get("source_signal_id")
                or getattr(fill, "signal_id", None)
            )
            repository = getattr(self.attribution_service, "signal_repository", None)
            if signal_id and repository is not None:
                repository.mark_filled(str(signal_id))
                result["signal_status"] = "FILLED"

        return result

    def _persist_signal_fill_linkage_v1(self, *, fill: Any, payload: dict | None) -> bool:
        """Русский комментарий: напрямую пишет связь signal_id -> fill_id в signal_fills."""
        if not isinstance(payload, dict):
            payload = {}

        signal_id = (
            payload.get("signal_id")
            or payload.get("source_signal_id")
            or getattr(fill, "signal_id", None)
        )

        if not signal_id:
            return False

        fill_id = getattr(fill, "fill_id", None)
        symbol = getattr(fill, "symbol", None) or payload.get("symbol")
        side = getattr(fill, "side", None) or payload.get("side")
        qty = float(getattr(fill, "qty", 0.0) or payload.get("qty") or 0.0)
        price = float(getattr(fill, "price", 0.0) or payload.get("price") or 0.0)

        if not symbol or not side or qty <= 0:
            return False

        database_url = os.getenv("DATABASE_URL", "")
        if not database_url:
            return False

        try:
            import psycopg

            with psycopg.connect(database_url) as conn:
                with conn.transaction():
                    conn.execute(
                        """
                        INSERT INTO signal_fills (
                            signal_id,
                            fill_id,
                            symbol,
                            side,
                            qty,
                            price,
                            created_at,
                            portfolio_scope
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, now(),
                                analytics.resolve_paper_portfolio_scope_v1(%s,'paper'))
                        """,
                        (
                            str(signal_id),
                            str(fill_id) if fill_id else None,
                            str(symbol),
                            str(side).upper(),
                            qty,
                            price,
                            str(symbol),
                        ),
                    )
            return True

        except Exception:
            return False

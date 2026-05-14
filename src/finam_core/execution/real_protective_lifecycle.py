from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ProtectiveLifecycleResult:
    executed: bool
    action: str
    order_id: str | None
    status: str
    reason: str


class RealProtectiveLifecycleEngine:
    """
    Русский комментарий:
    Реальный lifecycle защитных заявок.
    По умолчанию безопасен: без явного env-флага реальные заявки не отправляет.
    """

    def __init__(self, orders_client, link_repository=None) -> None:
        self.orders_client = orders_client
        self.link_repository = link_repository

    def enabled(self) -> bool:
        return (
            os.getenv("REAL_PROTECTIVE_LIFECYCLE_ENABLED", "0") == "1"
            and os.getenv("TRAILING_ORDER_DRY_RUN", "1") == "0"
        )

    def place_or_replace_stop(
        self,
        *,
        symbol: str,
        side: str,
        qty: float,
        stop_price: float,
        entry_order_id: str | None = None,
        old_order_id: str | None = None,
        reason: str = "protective_lifecycle",
    ) -> ProtectiveLifecycleResult:
        if not self.enabled():
            return ProtectiveLifecycleResult(
                executed=False,
                action="SKIP",
                order_id=None,
                status="DRY_RUN_OR_DISABLED",
                reason="real_protective_lifecycle_disabled",
            )

        if not symbol or side not in {"BUY", "SELL"} or qty <= 0 or stop_price <= 0:
            return ProtectiveLifecycleResult(False, "REJECT", None, "INVALID_INPUT", reason)

        try:
            if old_order_id and hasattr(self.orders_client, "cancel_order"):
                self.orders_client.cancel_order(order_id=old_order_id)

            result = self.orders_client.place_stop_order(
                symbol=symbol,
                side=side,
                qty=qty,
                stop_price=stop_price,
            )

            status = result.get("status") if isinstance(result, dict) else getattr(result, "status", None)
            order_id = result.get("order_id") if isinstance(result, dict) else getattr(result, "order_id", None)
            broker_reason = result.get("reason") if isinstance(result, dict) else getattr(result, "reason", None)

            if self.link_repository is not None and entry_order_id and order_id:
                self.link_repository.save(
                    entry_order_id=entry_order_id,
                    protective_order_id=str(order_id),
                    symbol=symbol,
                    side=side,
                    qty=qty,
                    stop_price=stop_price,
                    raw={
                        "reason": reason,
                        "old_order_id": old_order_id,
                        "broker_status": status,
                        "broker_reason": broker_reason,
                    },
                )

            return ProtectiveLifecycleResult(
                executed=True,
                action="PLACE_OR_REPLACE_STOP",
                order_id=str(order_id) if order_id else None,
                status=str(status or "UNKNOWN"),
                reason=str(broker_reason or reason),
            )

        except Exception as exc:
            return ProtectiveLifecycleResult(
                executed=False,
                action="ERROR",
                order_id=None,
                status="EXCEPTION",
                reason=f"{type(exc).__name__}:{exc}",
            )

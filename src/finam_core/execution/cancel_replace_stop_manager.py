# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CancelReplaceResult:
    symbol: str
    old_order_id: str
    new_order_id: str | None
    status: str
    reason: str | None = None


class CancelReplaceStopManager:
    """
    Русский комментарий:
    Безопасная замена защитного стопа:
    1) cancel old stop
    2) place new stop
    """

    def __init__(self, orders_client: Any, order_event_store: Any | None = None) -> None:
        self.orders_client = orders_client
        self.order_event_store = order_event_store

    def replace_stop(
        self,
        *,
        symbol: str,
        old_order_id: str,
        side: str,
        qty: float,
        stop_price: float,
    ) -> CancelReplaceResult:
        if not symbol or not old_order_id or side not in ("BUY", "SELL") or qty <= 0 or stop_price <= 0:
            return CancelReplaceResult(
                symbol=symbol,
                old_order_id=old_order_id,
                new_order_id=None,
                status="REJECTED",
                reason="invalid_replace_stop_request",
            )

        cancel_result = self.orders_client.cancel_order(old_order_id)

        if isinstance(cancel_result, dict) and cancel_result.get("status") not in ("CANCELED", "ACCEPTED", "OK"):
            return CancelReplaceResult(
                symbol=symbol,
                old_order_id=old_order_id,
                new_order_id=None,
                status="REJECTED",
                reason=str(cancel_result.get("reason") or "cancel_failed"),
            )

        place_result = self.orders_client.place_stop_order(
            symbol=symbol,
            side=side,
            qty=qty,
            stop_price=stop_price,
        )

        new_order_id = None
        status = "UNKNOWN"
        reason = None

        if isinstance(place_result, dict):
            new_order_id = place_result.get("order_id")
            status = str(place_result.get("status") or "UNKNOWN")
            reason = place_result.get("reason")
        else:
            new_order_id = getattr(place_result, "order_id", None)
            status = str(getattr(place_result, "status", "UNKNOWN"))
            reason = getattr(place_result, "reason", None)

        return CancelReplaceResult(
            symbol=symbol,
            old_order_id=old_order_id,
            new_order_id=new_order_id,
            status=status,
            reason=reason,
        )

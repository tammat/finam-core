from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FinamOrderStatusResult:
    ok: bool
    broker_status: str
    filled_qty: float
    avg_price: float
    reason: str


class FinamOrderStatusAdapter:
    def __init__(self, client: Any):
        self.client = client

    def get_status(
        self,
        *,
        broker_order_id: str,
        symbol: str | None = None,
    ) -> FinamOrderStatusResult:
        if not broker_order_id:
            return FinamOrderStatusResult(
                False,
                "UNKNOWN",
                0.0,
                0.0,
                "broker_order_id_empty",
            )

        if hasattr(self.client, "get_order_status"):
            result = self.client.get_order_status(
                broker_order_id=broker_order_id
            )

        elif hasattr(self.client, "get_order"):
            result = self.client.get_order(
                broker_order_id=broker_order_id
            )

        else:
            return FinamOrderStatusResult(
                False,
                "UNKNOWN",
                0.0,
                0.0,
                "client_has_no_status_method",
            )

        if result is None:
            return FinamOrderStatusResult(
                False,
                "UNKNOWN",
                0.0,
                0.0,
                "order_not_found",
            )

        status = str(
            result.get("status")
            or result.get("order_status")
            or result.get("state")
            or "UNKNOWN"
        )

        filled_qty = float(
            result.get("filled_qty")
            or result.get("executed_qty")
            or 0.0
        )

        avg_price = float(
            result.get("avg_price")
            or result.get("average_price")
            or 0.0
        )

        return FinamOrderStatusResult(
            True,
            status,
            filled_qty,
            avg_price,
            "status_loaded",
        )

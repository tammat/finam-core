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


    def _find_order(self, *, orders, broker_order_id: str):
        """Русский комментарий: ищет заявку по order_id в списке dict/protobuf объектов."""
        target = str(broker_order_id)

        for item in list(orders or []):
            if isinstance(item, dict):
                oid = (
                    item.get("order_id")
                    or item.get("broker_order_id")
                    or item.get("transaction_id")
                )
            else:
                oid = getattr(item, "order_id", None)

            if str(oid) == target:
                return item

        return None

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

        elif hasattr(self.client, "get_orders"):
            orders = self.client.get_orders()
            result = self._find_order(
                orders=orders,
                broker_order_id=broker_order_id,
            )

        elif hasattr(self.client, "get_open_orders"):
            orders = self.client.get_open_orders()
            result = self._find_order(
                orders=orders,
                broker_order_id=broker_order_id,
            )

        elif hasattr(self.client, "list_open_orders"):
            orders = self.client.list_open_orders()
            result = self._find_order(
                orders=orders,
                broker_order_id=broker_order_id,
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

        if isinstance(result, dict):
            status = str(
                result.get("status")
                or result.get("order_status")
                or result.get("state")
                or "UNKNOWN"
            )

            filled_qty = float(
                result.get("filled_qty")
                or result.get("executed_qty")
                or result.get("executed_quantity")
                or 0.0
            )

            avg_price = float(
                result.get("avg_price")
                or result.get("average_price")
                or result.get("avg_execution_price")
                or result.get("price")
                or 0.0
            )

            return FinamOrderStatusResult(
                True,
                status,
                filled_qty,
                avg_price,
                "status_loaded",
            )

        status = str(getattr(result, "status", "UNKNOWN"))

        executed_obj = getattr(result, "executed_quantity", None)

        try:
            filled_qty = float(getattr(executed_obj, "value", executed_obj) or 0.0)
        except Exception:
            filled_qty = 0.0

        return FinamOrderStatusResult(
            True,
            status,
            filled_qty,
            0.0,
            "protobuf_status_loaded",
        )

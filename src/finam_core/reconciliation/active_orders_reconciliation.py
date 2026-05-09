from __future__ import annotations

from dataclasses import dataclass
from finam_core.oms.broker_status_mapper import BrokerStatusMapper



def _execution_mode(position) -> str:
    """Русский комментарий: режим позиции нужен, чтобы не требовать broker orders для manual/paper/virtual."""
    if isinstance(position, dict):
        raw = (
            position.get("execution_mode")
            or position.get("mode")
            or position.get("source")
            or position.get("position_mode")
            or ""
        )
    else:
        raw = (
            getattr(position, "execution_mode", None)
            or getattr(position, "mode", None)
            or getattr(position, "source", None)
            or getattr(position, "position_mode", None)
            or ""
        )

    mode = str(raw or "").strip().lower()
    return mode or "unknown"


def _requires_broker_orders(position) -> bool:
    """Русский комментарий: broker stop/take orders обязательны только для real managed positions."""
    return _execution_mode(position) == "real"


ACTIVE_STATUSES = {
    "NEW",
    "WORKING",
    "WATCHING",
    "PENDING_NEW",
    "ACCEPTED",
    "ORDER_STATUS_NEW",
    "ORDER_STATUS_WATCHING",
    "ORDER_STATUS_PENDING_NEW",
}

_BROKER_STATUS_MAPPER = BrokerStatusMapper()


def map_broker_order_status(order) -> str:
    """Русский комментарий: нормализует broker status в OMS status для reconciliation."""
    if isinstance(order, dict):
        mapping = _BROKER_STATUS_MAPPER.map_order(order)
    else:
        raw_status = None
        for attr in ("status", "orderStatus", "state", "order_state"):
            if hasattr(order, attr):
                raw_status = getattr(order, attr)
                break
        mapping = _BROKER_STATUS_MAPPER.map_status(raw_status)
    return mapping.oms_status.value



@dataclass(frozen=True)
class ActiveOrderIssue:
    symbol: str
    kind: str
    order_id: str | None
    message: str


class ActiveOrdersReconciliation:
    def __init__(self, orders_client, managed_service):
        self.orders_client = orders_client
        self.managed = managed_service

    def check(self) -> list[ActiveOrderIssue]:
        orders = self._get_active_orders()
        by_id = {str(o.get("order_id")): o for o in orders if o.get("order_id")}

        issues: list[ActiveOrderIssue] = []

        for pos in self.managed.repository.list_all():
            expected_ids = [
                ("stop_order_id", pos.stop_order_id),
                ("tp1_order_id", pos.tp1_order_id),
                ("tp2_order_id", pos.tp2_order_id),
            ]

            for field, order_id in expected_ids:
                if not order_id:
                    issues.append(ActiveOrderIssue(
                        symbol=pos.symbol,
                        kind=f"missing_{field}",
                        order_id=None,
                        message=f"{field} is not registered in managed_positions",
                    ))
                    continue

                if str(order_id) not in by_id:
                    issues.append(ActiveOrderIssue(
                        symbol=pos.symbol,
                        kind=f"broker_order_not_found:{field}",
                        order_id=str(order_id),
                        message=f"{field} exists in managed_positions but not active at broker",
                    ))

        return issues

    def _get_active_orders(self) -> list[dict]:
        if hasattr(self.orders_client, "get_orders"):
            orders = self.orders_client.get_orders()
        elif hasattr(self.orders_client, "subscribe_orders"):
            orders = self.orders_client.subscribe_orders(max_events=50)
        else:
            return []

        active = []
        for o in orders or []:
            status = str(o.get("status") or "").upper()
            if status in ACTIVE_STATUSES:
                active.append(o)

        return active

from __future__ import annotations

from dataclasses import dataclass

from finam_core.oms.order_state_machine import OrderStatus


@dataclass(frozen=True)
class BrokerStatusMapping:
    broker_status: str
    oms_status: OrderStatus
    reason: str


class BrokerStatusMapper:
    """Русский комментарий: нормализует broker/order statuses в статусы OMS."""

    FINAM_STATUS_MAP: dict[str, OrderStatus] = {
        # Common / REST-like
        "NEW": OrderStatus.ACCEPTED,
        "WORKING": OrderStatus.ACCEPTED,
        "ACTIVE": OrderStatus.ACCEPTED,
        "ACCEPTED": OrderStatus.ACCEPTED,
        "PENDING_NEW": OrderStatus.SENT,
        "PENDING": OrderStatus.SENT,

        # Filled
        "MATCHED": OrderStatus.FILLED,
        "FILLED": OrderStatus.FILLED,
        "DONE": OrderStatus.FILLED,
        "EXECUTED": OrderStatus.FILLED,

        # Partial
        "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
        "PARTIAL_FILL": OrderStatus.PARTIALLY_FILLED,
        "PARTIAL": OrderStatus.PARTIALLY_FILLED,

        # Cancelled
        "CANCELLED": OrderStatus.CANCELLED,
        "CANCELED": OrderStatus.CANCELLED,
        "CANCELLED_BY_USER": OrderStatus.CANCELLED,

        # Rejected
        "REJECTED": OrderStatus.REJECTED,
        "DECLINED": OrderStatus.REJECTED,
        "DENIED": OrderStatus.REJECTED,

        # Expired / failed
        "EXPIRED": OrderStatus.EXPIRED,
        "FAILED": OrderStatus.FAILED,
        "ERROR": OrderStatus.FAILED,

        # gRPC enum-like
        "ORDER_STATUS_NEW": OrderStatus.ACCEPTED,
        "ORDER_STATUS_WORKING": OrderStatus.ACCEPTED,
        "ORDER_STATUS_WATCHING": OrderStatus.ACCEPTED,
        "ORDER_STATUS_PENDING_NEW": OrderStatus.SENT,
        "ORDER_STATUS_MATCHED": OrderStatus.FILLED,
        "ORDER_STATUS_PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
        "ORDER_STATUS_CANCELLED": OrderStatus.CANCELLED,
        "ORDER_STATUS_CANCELED": OrderStatus.CANCELLED,
        "ORDER_STATUS_REJECTED": OrderStatus.REJECTED,
        "ORDER_STATUS_EXPIRED": OrderStatus.EXPIRED,
    }

    def normalize_raw(self, broker_status: str | None) -> str:
        if broker_status is None:
            return ""
        return str(broker_status).strip().upper()

    def map_status(self, broker_status: str | None) -> BrokerStatusMapping:
        raw = self.normalize_raw(broker_status)

        if not raw:
            return BrokerStatusMapping(
                broker_status="",
                oms_status=OrderStatus.FAILED,
                reason="empty_broker_status",
            )

        oms_status = self.FINAM_STATUS_MAP.get(raw)

        if oms_status is None:
            return BrokerStatusMapping(
                broker_status=raw,
                oms_status=OrderStatus.FAILED,
                reason=f"unknown_broker_status:{raw}",
            )

        return BrokerStatusMapping(
            broker_status=raw,
            oms_status=oms_status,
            reason="mapped",
        )

    def map_order(self, order: dict) -> BrokerStatusMapping:
        """Русский комментарий: вытаскивает статус из разных форматов broker order."""
        for key in ("status", "orderStatus", "state", "order_state"):
            if key in order:
                return self.map_status(order.get(key))

        return BrokerStatusMapping(
            broker_status="",
            oms_status=OrderStatus.FAILED,
            reason="broker_status_field_missing",
        )

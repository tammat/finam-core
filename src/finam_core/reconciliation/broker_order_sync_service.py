from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finam_core.oms.order_journal import OmsOrderJournal
from finam_core.events.event_audit import append_event_safe


@dataclass(frozen=True)
class BrokerOrderSyncIssue:
    symbol: str
    order_id: str | None
    client_order_id: str | None
    kind: str
    message: str


@dataclass(frozen=True)
class BrokerOrderSyncResult:
    synced: int
    failed: int
    issues: list[BrokerOrderSyncIssue]


class BrokerOrderSyncService:
    """Русский комментарий: синхронизирует broker active orders с OMS journal."""

    def __init__(
        self,
        *,
        orders_client: Any,
        oms_journal: OmsOrderJournal | None = None,
    ) -> None:
        self.orders_client = orders_client
        self.oms_journal = oms_journal or OmsOrderJournal()

    def _load_orders(self) -> list[dict]:
        if hasattr(self.orders_client, "get_orders"):
            orders = self.orders_client.get_orders()
        elif hasattr(self.orders_client, "subscribe_orders"):
            orders = self.orders_client.subscribe_orders(max_events=50)
        else:
            return []

        return list(orders or [])

    @staticmethod
    def _field(order: dict, *names: str):
        for name in names:
            if name in order:
                return order.get(name)
        return None

    def sync_once(self) -> BrokerOrderSyncResult:
        """Русский комментарий: один проход sync broker orders -> OMS."""
        orders = self._load_orders()

        synced = 0
        issues: list[BrokerOrderSyncIssue] = []

        for order in orders:
            symbol = str(self._field(order, "symbol", "ticker") or "UNKNOWN")
            order_id = self._field(order, "order_id", "orderId", "broker_order_id", "brokerOrderId")
            client_order_id = self._field(order, "client_order_id", "clientOrderId", "client_id", "clientId")

            if not client_order_id:
                issues.append(
                    BrokerOrderSyncIssue(
                        symbol=symbol,
                        order_id=str(order_id) if order_id else None,
                        client_order_id=None,
                        kind="missing_client_order_id",
                        message="broker order cannot be synced without client_order_id",
                    )
                )
                continue

            try:
                mapping = self.oms_journal.update_status_from_broker_order(order)
                synced += 1
                print(
                    f"BROKER_ORDER_SYNC_OK client_order_id={client_order_id} "
                    f"order_id={order_id} symbol={symbol} oms_status={mapping.oms_status.value}",
                    flush=True,
                )
                append_event_safe(
                    event_type="BROKER_ORDER_SYNC_OK",
                    aggregate_type="order",
                    aggregate_id=str(client_order_id),
                    source="broker_order_sync_service",
                    payload={
                        "client_order_id": str(client_order_id),
                        "order_id": str(order_id) if order_id else None,
                        "symbol": symbol,
                        "oms_status": mapping.oms_status.value,
                    },
                )
            except Exception as exc:
                issues.append(
                    BrokerOrderSyncIssue(
                        symbol=symbol,
                        order_id=str(order_id) if order_id else None,
                        client_order_id=str(client_order_id),
                        kind="oms_update_failed",
                        message=str(exc),
                    )
                )
                append_event_safe(
                    event_type="BROKER_ORDER_SYNC_FAILED",
                    aggregate_type="order",
                    aggregate_id=str(client_order_id),
                    source="broker_order_sync_service",
                    payload={
                        "client_order_id": str(client_order_id),
                        "order_id": str(order_id) if order_id else None,
                        "symbol": symbol,
                        "error": str(exc),
                    },
                )

        return BrokerOrderSyncResult(
            synced=synced,
            failed=len(issues),
            issues=issues,
        )

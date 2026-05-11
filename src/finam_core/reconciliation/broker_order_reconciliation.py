# -*- coding: utf-8 -*-
"""
BrokerOrderReconciliationService.

Русский комментарий: сверяет локальные ACK после PlaceOrder с состоянием заявок у брокера.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrokerOrderState:
    order_id: str
    symbol: str
    side: str
    status: str
    qty: float = 0.0
    filled_qty: float = 0.0


@dataclass(frozen=True)
class BrokerOrderReconciliationIssue:
    order_id: str | None
    symbol: str
    issue_type: str
    reason: str


class BrokerOrderReconciliationService:
    def __init__(self, broker_orders: list[BrokerOrderState]) -> None:
        self.broker_orders = {o.order_id: o for o in broker_orders if o.order_id}

    def check_ack(self, ack) -> list[BrokerOrderReconciliationIssue]:
        issues: list[BrokerOrderReconciliationIssue] = []

        order_id = getattr(ack, "order_id", None)
        symbol = str(getattr(ack, "symbol", "") or "")

        if not order_id:
            issues.append(
                BrokerOrderReconciliationIssue(
                    order_id=None,
                    symbol=symbol,
                    issue_type="ACK_WITHOUT_ORDER_ID",
                    reason="ack_has_no_order_id",
                )
            )
            return issues

        broker_order = self.broker_orders.get(order_id)
        if broker_order is None:
            issues.append(
                BrokerOrderReconciliationIssue(
                    order_id=order_id,
                    symbol=symbol,
                    issue_type="ACK_MISSING_AT_BROKER",
                    reason="ack_order_id_not_found_in_broker_orders",
                )
            )
            return issues

        broker_status = broker_order.status.upper()
        if broker_status in ("REJECTED", "FAILED", "CANCELED", "CANCELLED", "EXPIRED"):
            issues.append(
                BrokerOrderReconciliationIssue(
                    order_id=order_id,
                    symbol=symbol,
                    issue_type="BROKER_ORDER_NOT_ACTIVE",
                    reason=f"broker_status={broker_order.status}",
                )
            )

        return issues

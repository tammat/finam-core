# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class OcoGroup:
    group_id: str
    symbol: str
    first_order_id: str
    second_order_id: str
    status: str = "ACTIVE"
    triggered_order_id: str | None = None
    canceled_order_id: str | None = None
    reason: str | None = None


@dataclass
class OcoHandleResult:
    group_id: str
    status: str
    triggered_order_id: str | None = None
    canceled_order_id: str | None = None
    reason: str | None = None


class OcoOrderManager:
    """
    Русский комментарий:
    OCO = One Cancels Other. Менеджер хранит пары заявок и отменяет вторую,
    когда первая становится исполненной. Сам заявки не создаёт.
    """

    FILLED_STATUSES = {"FILLED", "EXECUTED", "SL_EXECUTED", "TP_EXECUTED"}
    INACTIVE_STATUSES = {"CANCELED", "CANCELLED", "REJECTED", "DISABLED", "EXPIRED"}

    def __init__(self, orders_client: Any, order_event_store: Any | None = None) -> None:
        self.orders_client = orders_client
        self.order_event_store = order_event_store
        self._groups: dict[str, OcoGroup] = {}
        self._order_to_group: dict[str, str] = {}

    def register_group(
        self,
        *,
        group_id: str,
        symbol: str,
        first_order_id: str,
        second_order_id: str,
    ) -> OcoGroup:
        if not group_id or not symbol or not first_order_id or not second_order_id:
            raise ValueError("invalid_oco_group")
        if first_order_id == second_order_id:
            raise ValueError("oco_orders_must_be_different")

        group = OcoGroup(
            group_id=group_id,
            symbol=symbol,
            first_order_id=first_order_id,
            second_order_id=second_order_id,
        )
        self._groups[group_id] = group
        self._order_to_group[first_order_id] = group_id
        self._order_to_group[second_order_id] = group_id
        return group

    def get_group(self, group_id: str) -> OcoGroup | None:
        return self._groups.get(group_id)

    def handle_order_event(self, event: dict) -> OcoHandleResult | None:
        """Русский комментарий: обрабатывает событие заявки из SubscribeOrders/GetOrders."""
        order_id = str(event.get("order_id") or "")
        if not order_id:
            return None

        group_id = self._order_to_group.get(order_id)
        if not group_id:
            return None

        group = self._groups.get(group_id)
        if group is None:
            return None

        if group.status != "ACTIVE":
            return OcoHandleResult(
                group_id=group.group_id,
                status=group.status,
                triggered_order_id=group.triggered_order_id,
                canceled_order_id=group.canceled_order_id,
                reason="group_not_active",
            )

        status = str(event.get("status") or "").upper()

        if status in self.INACTIVE_STATUSES:
            return OcoHandleResult(
                group_id=group.group_id,
                status="ACTIVE",
                reason=f"ignored_inactive_status:{status}",
            )

        if status not in self.FILLED_STATUSES:
            return OcoHandleResult(
                group_id=group.group_id,
                status="ACTIVE",
                reason=f"ignored_status:{status}",
            )

        other_order_id = group.second_order_id if order_id == group.first_order_id else group.first_order_id
        cancel_result = self.orders_client.cancel_order(other_order_id)

        if isinstance(cancel_result, dict):
            cancel_status = str(cancel_result.get("status") or "").upper()
        else:
            cancel_status = str(getattr(cancel_result, "status", "") or "").upper()

        group.triggered_order_id = order_id
        group.canceled_order_id = other_order_id

        if cancel_status in {"CANCELED", "CANCELLED", "ACCEPTED", "OK", "DRY_RUN_CANCEL"}:
            group.status = "TRIGGERED"
            group.reason = "other_order_cancelled"
        else:
            group.status = "CANCEL_FAILED"
            group.reason = f"cancel_failed:{cancel_status}"

        return OcoHandleResult(
            group_id=group.group_id,
            status=group.status,
            triggered_order_id=group.triggered_order_id,
            canceled_order_id=group.canceled_order_id,
            reason=group.reason,
        )

# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finam_core.execution.protection_level_calculator import ProtectionLevelCalculator


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
    stop_loss_order_id: str | None = None
    take_profit_order_id: str | None = None
    protection_by_order_id: dict[str, dict[str, Any]] | None = None
    stop_loss_order_id: str | None = None
    take_profit_order_id: str | None = None


@dataclass
class OcoHandleResult:
    group_id: str
    status: str
    triggered_order_id: str | None = None
    canceled_order_id: str | None = None
    reason: str | None = None
    stop_loss_order_id: str | None = None
    take_profit_order_id: str | None = None


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

    def build_protection_by_order_id(
        self,
        *,
        symbol: str,
        first_order_id: str,
        first_side: str,
        first_entry_price: float,
        second_order_id: str,
        second_side: str,
        second_entry_price: float,
        atr: float,
        equity: float,
        risk_pct: float = 0.005,
        stop_atr_mult: float = 2.0,
        reward_risk: float = 2.0,
        point_value: float = 1.0,
        max_qty: int = 1,
        tick_size: float = 0.01,
    ) -> dict[str, dict[str, Any]]:
        """Русский комментарий: строит SL/TP protection config для обеих OCO-заявок."""
        calculator = ProtectionLevelCalculator()

        first_levels = calculator.calculate(
            symbol=symbol,
            entry_side=str(first_side).upper(),
            entry_price=float(first_entry_price),
            atr=float(atr),
            equity=float(equity),
            risk_pct=float(risk_pct),
            stop_atr_mult=float(stop_atr_mult),
            reward_risk=float(reward_risk),
            point_value=float(point_value),
            max_qty=int(max_qty),
            tick_size=float(tick_size),
        )

        second_levels = calculator.calculate(
            symbol=symbol,
            entry_side=str(second_side).upper(),
            entry_price=float(second_entry_price),
            atr=float(atr),
            equity=float(equity),
            risk_pct=float(risk_pct),
            stop_atr_mult=float(stop_atr_mult),
            reward_risk=float(reward_risk),
            point_value=float(point_value),
            max_qty=int(max_qty),
            tick_size=float(tick_size),
        )

        return {
            first_order_id: {
                "exit_side": first_levels.exit_side,
                "qty": first_levels.qty,
                "stop_loss_price": first_levels.stop_loss_price,
                "take_profit_price": first_levels.take_profit_price,
                "risk_per_unit": first_levels.risk_per_unit,
                "reward_per_unit": first_levels.reward_per_unit,
                "rr": first_levels.rr,
            },
            second_order_id: {
                "exit_side": second_levels.exit_side,
                "qty": second_levels.qty,
                "stop_loss_price": second_levels.stop_loss_price,
                "take_profit_price": second_levels.take_profit_price,
                "risk_per_unit": second_levels.risk_per_unit,
                "reward_per_unit": second_levels.reward_per_unit,
                "rr": second_levels.rr,
            },
        }


    def register_group(
        self,
        *,
        group_id: str,
        symbol: str,
        first_order_id: str,
        second_order_id: str,
        protection_by_order_id: dict[str, dict[str, Any]] | None = None,
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
            protection_by_order_id=protection_by_order_id or {},
        )
        self._groups[group_id] = group
        self._order_to_group[first_order_id] = group_id
        self._order_to_group[second_order_id] = group_id
        return group

    def get_group(self, group_id: str) -> OcoGroup | None:
        return self._groups.get(group_id)

    def _place_protection_orders(self, group: OcoGroup, triggered_order_id: str) -> tuple[str | None, str | None, str | None]:
        """Русский комментарий: после исполнения OCO ставит stop-loss и take-profit."""
        protection = (group.protection_by_order_id or {}).get(triggered_order_id) or {}
        if not protection:
            return None, None, "protection_not_configured"

        exit_side = str(protection.get("exit_side") or "").upper()
        qty = float(protection.get("qty") or 0.0)
        stop_loss_price = float(protection.get("stop_loss_price") or 0.0)
        take_profit_price = float(protection.get("take_profit_price") or 0.0)

        if exit_side not in ("BUY", "SELL") or qty <= 0:
            return None, None, "invalid_protection_config"

        stop_loss_order_id = None
        take_profit_order_id = None

        if stop_loss_price > 0:
            stop_result = self.orders_client.place_stop_order(
                symbol=group.symbol,
                side=exit_side,
                qty=qty,
                stop_price=stop_loss_price,
            )
            stop_loss_order_id = stop_result.get("order_id") if isinstance(stop_result, dict) else getattr(stop_result, "order_id", None)

        if take_profit_price > 0:
            if hasattr(self.orders_client, "place_take_profit_order"):
                take_result = self.orders_client.place_take_profit_order(
                    symbol=group.symbol,
                    side=exit_side,
                    qty=qty,
                    take_price=take_profit_price,
                )
            elif hasattr(self.orders_client, "place_limit_order"):
                take_result = self.orders_client.place_limit_order(
                    symbol=group.symbol,
                    side=exit_side,
                    qty=qty,
                    limit_price=take_profit_price,
                )
            else:
                take_result = {"status": "SKIPPED", "reason": "take_profit_method_not_available"}

            take_profit_order_id = take_result.get("order_id") if isinstance(take_result, dict) else getattr(take_result, "order_id", None)

        return stop_loss_order_id, take_profit_order_id, None


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

        stop_loss_order_id, take_profit_order_id, protection_reason = self._place_protection_orders(group, order_id)
        group.stop_loss_order_id = stop_loss_order_id
        group.take_profit_order_id = take_profit_order_id

        if cancel_status in {"CANCELED", "CANCELLED", "ACCEPTED", "OK", "DRY_RUN_CANCEL"}:
            group.status = "TRIGGERED"
            group.reason = protection_reason or "other_order_cancelled_and_protection_placed"
        else:
            group.status = "CANCEL_FAILED"
            group.reason = f"cancel_failed:{cancel_status}"

        return OcoHandleResult(
            group_id=group.group_id,
            status=group.status,
            triggered_order_id=group.triggered_order_id,
            canceled_order_id=group.canceled_order_id,
            reason=group.reason,
            stop_loss_order_id=group.stop_loss_order_id,
            take_profit_order_id=group.take_profit_order_id,
        )

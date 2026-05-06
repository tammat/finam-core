# -*- coding: utf-8 -*-
from __future__ import annotations


class OpenOrdersSync:
    """Русский комментарий: read-only группировка активных брокерских заявок по инструменту."""

    ACTIVE_STATUSES = {"WATCHING", "ACTIVE", "WORKING", "ACCEPTED", "NEW", "PARTIAL_FILLED"}

    def normalize_order(self, order: dict) -> dict:
        return {
            "order_id": str(order.get("order_id") or order.get("id") or ""),
            "symbol": str(order.get("symbol") or order.get("ticker") or ""),
            "side": str(order.get("side") or "").upper(),
            "status": str(order.get("status") or order.get("state") or "").upper(),
            "order_type": str(order.get("order_type") or order.get("type") or "").upper(),
            "price": order.get("price"),
            "stop_price": order.get("stop_price") or order.get("stop"),
            "qty": float(order.get("qty") or order.get("quantity") or 0.0),
            "raw": order,
        }

    def build_orders_by_symbol(self, orders: list[dict]) -> dict[str, list[dict]]:
        result: dict[str, list[dict]] = {}

        for raw in orders or []:
            order = self.normalize_order(raw)
            symbol = order["symbol"]
            status = order["status"]

            if not symbol:
                continue

            if status and status not in self.ACTIVE_STATUSES:
                continue

            result.setdefault(symbol, []).append(order)

        return result

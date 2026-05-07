# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any


class OrderRouter:
    """
    Русский комментарий:
    OrderRouter не отправляет заявки брокеру.
    Он только переводит execution_action/order_type в безопасный маршрут:
    MARKET -> real_execution
    STOP   -> stop_order
    LIMIT  -> limit_order
    SKIP   -> no_order
    """

    def route(self, intent: dict[str, Any], market_state: dict[str, Any] | None = None) -> dict[str, Any]:
        market_state = market_state or {}

        symbol = str(intent.get("symbol") or market_state.get("symbol") or "")
        side = str(intent.get("side") or "").upper()
        qty = float(intent.get("qty") or 0.0)
        action = str(intent.get("execution_action") or intent.get("order_type") or "").upper()

        if not symbol or side not in ("BUY", "SELL") or qty <= 0:
            return {
                "route": "SKIP",
                "order_type": "NONE",
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "reason": "invalid_route_intent",
            }

        if action == "MARKET":
            return {
                "route": "REAL_EXECUTION",
                "order_type": "MARKET",
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "price": intent.get("price") or market_state.get("last"),
                "reason": intent.get("execution_reason") or "market_execution",
            }

        if action == "STOP":
            stop_price = intent.get("stop_price")
            if stop_price is None:
                return {
                    "route": "SKIP",
                    "order_type": "NONE",
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "reason": "missing_stop_price",
                }

            return {
                "route": "STOP_ORDER",
                "order_type": "STOP",
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "stop_price": float(stop_price),
                "reason": intent.get("execution_reason") or "stop_order_route",
            }

        if action == "LIMIT":
            limit_price = intent.get("limit_price") or intent.get("entry_price") or intent.get("price")
            if limit_price is None:
                return {
                    "route": "SKIP",
                    "order_type": "NONE",
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "reason": "missing_limit_price",
                }

            return {
                "route": "LIMIT_ORDER",
                "order_type": "LIMIT",
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "limit_price": float(limit_price),
                "stop_loss": intent.get("stop_loss"),
                "take_profit": intent.get("take_profit"),
                "entry_price": intent.get("entry_price"),
                "reason": intent.get("execution_reason") or intent.get("entry_reason") or "limit_order_route",
            }

        return {
            "route": "SKIP",
            "order_type": "NONE",
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "reason": f"unsupported_execution_action:{action}",
        }

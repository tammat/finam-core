# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExecutionDispatchResult:
    """Русский комментарий: результат технической отправки выбранного маршрута."""

    symbol: str
    side: str
    qty: float
    route: str
    status: str
    order_id: str | None = None
    reason: str | None = None
    raw: Any | None = None


class ExecutionDispatcher:
    """
    Русский комментарий:
    Исполняет маршрут, выбранный OrderRouter.
    Сам не принимает торговых решений.
    """

    def __init__(self, *, orders_client: Any = None, real_execution_engine: Any = None) -> None:
        self.orders_client = orders_client
        self.real_execution_engine = real_execution_engine

    def dispatch(self, routed_intent: dict[str, Any], market_state: dict[str, Any] | None = None) -> ExecutionDispatchResult:
        market_state = market_state or {}

        route = str(routed_intent.get("order_route") or routed_intent.get("route") or "").upper()
        symbol = str(routed_intent.get("symbol") or market_state.get("symbol") or "")
        side = str(routed_intent.get("side") or "").upper()
        qty = float(routed_intent.get("qty") or 0.0)

        if not symbol or side not in ("BUY", "SELL") or qty <= 0:
            return ExecutionDispatchResult(symbol, side, qty, route or "SKIP", "REJECTED", reason="invalid_dispatch_intent")

        if route == "SKIP":
            return ExecutionDispatchResult(symbol, side, qty, route, "SKIPPED", reason="router_skip")

        if route == "STOP_ORDER":
            return self._dispatch_stop_order(symbol, side, qty, routed_intent)

        if route == "LIMIT_ORDER":
            return self._dispatch_limit_order(symbol, side, qty, routed_intent)

        if route == "REAL_EXECUTION":
            return self._dispatch_real_execution(symbol, side, qty, routed_intent, market_state)

        return ExecutionDispatchResult(symbol, side, qty, route or "UNKNOWN", "REJECTED", reason=f"unsupported_route:{route}")

    def _dispatch_stop_order(self, symbol: str, side: str, qty: float, routed_intent: dict[str, Any]) -> ExecutionDispatchResult:
        if self.orders_client is None or not hasattr(self.orders_client, "place_stop_order"):
            return ExecutionDispatchResult(symbol, side, qty, "STOP_ORDER", "REJECTED", reason="orders_client_stop_not_configured")

        stop_price = routed_intent.get("stop_price")
        if stop_price is None:
            return ExecutionDispatchResult(symbol, side, qty, "STOP_ORDER", "REJECTED", reason="missing_stop_price")

        result = self.orders_client.place_stop_order(
            symbol=symbol,
            side=side,
            qty=qty,
            stop_price=float(stop_price),
        )

        return self._normalize_result(symbol, side, qty, "STOP_ORDER", result)

    def _dispatch_limit_order(self, symbol: str, side: str, qty: float, routed_intent: dict[str, Any]) -> ExecutionDispatchResult:
        if self.orders_client is None or not hasattr(self.orders_client, "place_limit_order"):
            return ExecutionDispatchResult(symbol, side, qty, "LIMIT_ORDER", "REJECTED", reason="orders_client_limit_not_configured")

        limit_price = routed_intent.get("limit_price")
        if limit_price is None:
            return ExecutionDispatchResult(symbol, side, qty, "LIMIT_ORDER", "REJECTED", reason="missing_limit_price")

        result = self.orders_client.place_limit_order(
            symbol=symbol,
            side=side,
            qty=qty,
            limit_price=float(limit_price),
        )

        return self._normalize_result(symbol, side, qty, "LIMIT_ORDER", result)

    def _dispatch_real_execution(
        self,
        symbol: str,
        side: str,
        qty: float,
        routed_intent: dict[str, Any],
        market_state: dict[str, Any],
    ) -> ExecutionDispatchResult:
        if self.real_execution_engine is None or not hasattr(self.real_execution_engine, "execute"):
            return ExecutionDispatchResult(symbol, side, qty, "REAL_EXECUTION", "REJECTED", reason="real_execution_engine_not_configured")

        result = self.real_execution_engine.execute(routed_intent, market_state)
        status = str(getattr(result, "status", "") or "UNKNOWN")

        return ExecutionDispatchResult(
            symbol=str(getattr(result, "symbol", symbol)),
            side=str(getattr(result, "side", side)),
            qty=float(getattr(result, "qty", qty) or qty),
            route="REAL_EXECUTION",
            status=status,
            order_id=getattr(result, "order_id", None),
            reason=getattr(result, "reason", None),
            raw=result,
        )

    @staticmethod
    def _normalize_result(symbol: str, side: str, qty: float, route: str, result: Any) -> ExecutionDispatchResult:
        if isinstance(result, dict):
            return ExecutionDispatchResult(
                symbol=str(result.get("symbol") or symbol),
                side=str(result.get("side") or side),
                qty=float(result.get("qty") or qty),
                route=route,
                status=str(result.get("status") or "UNKNOWN"),
                order_id=result.get("order_id"),
                reason=result.get("reason"),
                raw=result,
            )

        return ExecutionDispatchResult(
            symbol=str(getattr(result, "symbol", symbol)),
            side=str(getattr(result, "side", side)),
            qty=float(getattr(result, "qty", qty) or qty),
            route=route,
            status=str(getattr(result, "status", "UNKNOWN")),
            order_id=getattr(result, "order_id", None),
            reason=getattr(result, "reason", None),
            raw=result,
        )

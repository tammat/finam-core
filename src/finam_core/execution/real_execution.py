# src/finam_core/execution/real_execution.py

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from finam_core.execution.order_state_machine import OrderState


@dataclass
class RealOrderResult:
    symbol: str
    side: str
    qty: float
    price: float | None
    status: str
    order_id: str | None = None
    reason: str | None = None
    raw: dict | None = None


class RealExecutionEngine:
    """
    Русский комментарий:
    Реальный execution-слой.
    Стратегия не имеет права вызывать этот класс напрямую.
    Только pipeline после RiskEngine.
    """

    def __init__(self, orders_client: Any) -> None:
        self.orders_client = orders_client
        self.mode = os.getenv("EXECUTION_MODE", "paper").strip().lower()
        # Русский комментарий: локальный read-only реестр жизненного цикла заявок.
        self.orders_by_id: dict[str, OrderState] = {}

    def _register_order_state(self, symbol: str, side: str, qty: float, order_id: str | None = None) -> OrderState:
        """Русский комментарий: создаёт локальное состояние заявки до отправки брокеру."""
        oid = order_id or f"local_{symbol}_{side}_{len(self.orders_by_id) + 1}"
        state = OrderState(order_id=oid, symbol=symbol, side=side, qty=float(qty))
        self.orders_by_id[oid] = state
        return state


    def execute(self, intent: dict | None = None, market_state: dict | None = None, **kwargs) -> RealOrderResult:
        """Русский комментарий: поддерживает основной intent-контракт и безопасный keyword-вызов для тестов."""
        if intent is None:
            intent = {
                "symbol": kwargs.get("symbol"),
                "side": kwargs.get("side"),
                "qty": kwargs.get("qty"),
                "price": kwargs.get("price"),
            }

        symbol = str(intent.get("symbol") or "")
        side = str(intent.get("side") or "")
        qty = float(intent.get("qty") or 0.0)
        price = intent.get("price")

        if not symbol or side not in ("BUY", "SELL") or qty <= 0:
            return RealOrderResult(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                status="REJECTED",
                reason="invalid_order_intent",
            )

        order_state = self._register_order_state(symbol=symbol, side=side, qty=qty)
        order_state.on_submitted()

        if os.getenv("REAL_EXECUTION_ENABLED", "0") != "1":
            return RealOrderResult(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                status="REJECTED",
                reason="REAL_EXECUTION_ENABLED_not_enabled",
            )

        if os.getenv("REAL_ORDER_CONFIRM", "0") != "1":
            return RealOrderResult(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                status="REJECTED",
                reason="REAL_ORDER_CONFIRM_not_enabled",
            )

        if self.mode == "real_dry_run":
            order_state.on_accepted()
            return RealOrderResult(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                status="DRY_RUN_ACCEPTED",
                order_id=order_state.order_id,
            )

        if self.mode != "real":
            return RealOrderResult(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                status="REJECTED",
                reason=f"unsupported_execution_mode={self.mode}",
            )

        if self.orders_client is None:
            order_state.on_rejected("orders_client_not_configured")
            return RealOrderResult(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                status="REJECTED",
                order_id=order_state.order_id,
                reason="orders_client_not_configured",
            )

        result = self.orders_client.place_market_order(
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
        )

        if isinstance(result, RealOrderResult):
            return result

        if isinstance(result, dict):
            status = str(result.get("status") or "UNKNOWN")
            broker_order_id = result.get("order_id") or order_state.order_id

            if broker_order_id != order_state.order_id:
                self.orders_by_id.pop(order_state.order_id, None)
                order_state.order_id = str(broker_order_id)
                self.orders_by_id[order_state.order_id] = order_state

            if status in ("ACCEPTED", "DRY_RUN_ACCEPTED"):
                order_state.on_accepted()
            elif status in ("REJECTED", "ERROR"):
                order_state.on_rejected(str(result.get("reason") or status))

            return RealOrderResult(
                symbol=str(result.get("symbol") or symbol),
                side=str(result.get("side") or side),
                qty=float(result.get("qty") or qty),
                price=result.get("price", price),
                status=status,
                order_id=order_state.order_id,
                reason=result.get("reason"),
                raw=result,
            )

        return RealOrderResult(
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
            status=str(getattr(result, "status", "UNKNOWN")),
            order_id=getattr(result, "order_id", None),
            reason=getattr(result, "reason", None),
            raw={"result_type": type(result).__name__, "result_repr": repr(result)},
        )
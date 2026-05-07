# src/finam_core/execution/real_execution.py

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from finam_core.execution.order_state_machine import OrderState
from finam_core.execution.broker_capabilities_gate import BrokerCapabilities, BrokerCapabilitiesGate
from finam_core.storage.postgres_order_event_store import PostgresOrderEventStore



def build_capabilities_from_env() -> BrokerCapabilities:
    """Русский комментарий: профиль ограничений брокера задаётся через BROKER_CATEGORY."""
    category = os.getenv("BROKER_CATEGORY", "KNUR").strip().upper()

    if category == "KNUR":
        return BrokerCapabilities(
            category="KNUR",
            allow_api_orders=True,
            allow_long=True,
            allow_short=False,
            allow_margin=False,
            allow_futures=False,
        )

    if category in {"KSUR", "KPUR"}:
        return BrokerCapabilities(
            category=category,
            allow_api_orders=True,
            allow_long=True,
            allow_short=True,
            allow_margin=True,
            allow_futures=True,
        )

    return BrokerCapabilities(
        category=category,
        allow_api_orders=False,
        allow_long=False,
        allow_short=False,
        allow_margin=False,
        allow_futures=False,
    )


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

    def __init__(self, orders_client: Any, capabilities_gate: Any = None) -> None:
        self.orders_client = orders_client
        # Русский комментарий: финальная проверка категории клиента перед live-заявкой.
        self.capabilities_gate = capabilities_gate or BrokerCapabilitiesGate(build_capabilities_from_env())
        self.mode = os.getenv("EXECUTION_MODE", "paper").strip().lower()
        # Русский комментарий: локальный read-only реестр жизненного цикла заявок.
        self.orders_by_id: dict[str, OrderState] = {}
        # Русский комментарий: опциональное PostgreSQL-хранилище событий заявок.
        self.order_event_store = None
        if os.getenv("ENABLE_ORDER_EVENT_STORE", "0") == "1":
            try:
                self.order_event_store = PostgresOrderEventStore()
            except Exception:
                self.order_event_store = None

    def _register_order_state(self, symbol: str, side: str, qty: float, order_id: str | None = None) -> OrderState:
        """Русский комментарий: создаёт локальное состояние заявки до отправки брокеру."""
        oid = order_id or f"local_{symbol}_{side}_{len(self.orders_by_id) + 1}"
        state = OrderState(order_id=oid, symbol=symbol, side=side, qty=float(qty))
        self.orders_by_id[oid] = state
        return state


    def _log_order_state(self, order_state: OrderState, reason: str | None = None, raw_json: dict | None = None) -> None:
        """Русский комментарий: безопасно пишет lifecycle заявки в PostgreSQL, не влияя на торговый цикл."""
        if self.order_event_store is None:
            return

        try:
            self.order_event_store.log_event(
                order_id=order_state.order_id,
                symbol=order_state.symbol,
                side=order_state.side,
                state=order_state.state,
                qty=order_state.qty,
                filled_qty=order_state.filled_qty,
                remaining_qty=order_state.remaining_qty(),
                fill_price=None,
                avg_fill_price=order_state.avg_fill_price,
                reason=reason or order_state.reason,
                raw_json=raw_json or {},
            )
        except Exception as exc:
            print(f"ORDER_EVENT_STORE_LOG_FAILED order_id={order_state.order_id} error={exc}", flush=True)


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

        # Русский комментарий: финальный предохранитель перед real/dry-run execution.
        if os.getenv("ENABLE_REAL_EXECUTION_SAFETY_GATE", "0") == "1":
            allowlist_raw = os.getenv("REAL_EXECUTION_SYMBOL_ALLOWLIST", "").strip()
            allowlist = {item.strip() for item in allowlist_raw.split(",") if item.strip()}

            if allowlist and symbol not in allowlist:
                return RealOrderResult(
                    symbol=symbol,
                    side=side,
                    qty=qty,
                    price=price,
                    status="REJECTED",
                    reason=f"symbol_not_in_allowlist:{symbol}",
                )

            max_qty = float(os.getenv("REAL_EXECUTION_MAX_QTY", "1"))
            if abs(qty) > max_qty:
                return RealOrderResult(
                    symbol=symbol,
                    side=side,
                    qty=qty,
                    price=price,
                    status="REJECTED",
                    reason=f"qty_exceeds_max:{qty}>{max_qty}",
                )

        order_state = self._register_order_state(symbol=symbol, side=side, qty=qty)
        order_state.on_submitted()
        self._log_order_state(order_state, raw_json={"event": "SUBMITTED"})

        if os.getenv("REAL_EXECUTION_ENABLED", "0") != "1":
            order_state.on_rejected("REAL_EXECUTION_ENABLED_not_enabled")
            self._log_order_state(
                order_state,
                reason="REAL_EXECUTION_ENABLED_not_enabled",
                raw_json={"event": "REJECTED"},
            )
            return RealOrderResult(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                status="REJECTED",
                reason="REAL_EXECUTION_ENABLED_not_enabled",
            )

        if os.getenv("REAL_ORDER_CONFIRM", "0") != "1":
            order_state.on_rejected("REAL_ORDER_CONFIRM_not_enabled")
            self._log_order_state(
                order_state,
                reason="REAL_ORDER_CONFIRM_not_enabled",
                raw_json={"event": "REJECTED"},
            )
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
            self._log_order_state(
                order_state,
                raw_json={"event": "ACCEPTED", "mode": "real_dry_run"},
            )
            return RealOrderResult(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                status="DRY_RUN_ACCEPTED",
                order_id=order_state.order_id,
            )

        if self.mode != "real":
            reason = f"unsupported_execution_mode={self.mode}"
            order_state.on_rejected(reason)
            self._log_order_state(order_state, reason=reason, raw_json={"event": "REJECTED"})
            return RealOrderResult(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                status="REJECTED",
                reason=reason,
            )

        if self.orders_client is None:
            order_state.on_rejected("orders_client_not_configured")
            self._log_order_state(
                order_state,
                reason="orders_client_not_configured",
                raw_json={"event": "REJECTED"},
            )
            return RealOrderResult(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                status="REJECTED",
                order_id=order_state.order_id,
                reason="orders_client_not_configured",
            )

        instrument_type = str(intent.get("instrument_type") or intent.get("asset_class") or "STOCK").upper()
        ok, gate_reason = self.capabilities_gate.validate_order(
            instrument_type=instrument_type,
            side=side,
            qty=qty,
        )
        if not ok:
            order_state.on_rejected(gate_reason)
            self._log_order_state(
                order_state,
                reason=gate_reason,
                raw_json={"event": "REJECTED", "gate": "BrokerCapabilitiesGate", "instrument_type": instrument_type},
            )
            return RealOrderResult(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                status="REJECTED",
                order_id=order_state.order_id,
                reason=gate_reason,
                raw={"gate": "BrokerCapabilitiesGate", "instrument_type": instrument_type},
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

            self._log_order_state(
                order_state,
                reason=result.get("reason"),
                raw_json={"event": order_state.state, "broker_result": result},
            )

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

    def on_fill(self, order_id: str, fill_qty: float, fill_price: float) -> RealOrderResult:
        """Русский комментарий: применяет fill к локальному OrderState и пишет PARTIAL_FILLED/FILLED."""
        order_state = self.orders_by_id.get(order_id)
        if order_state is None:
            return RealOrderResult(
                symbol="",
                side="",
                qty=0.0,
                price=fill_price,
                status="REJECTED",
                order_id=order_id,
                reason="unknown_order_id",
            )

        order_state.on_partial_fill(fill_qty, fill_price)
        self._log_order_state(
            order_state,
            raw_json={"event": order_state.state, "fill_qty": fill_qty, "fill_price": fill_price},
        )

        return RealOrderResult(
            symbol=order_state.symbol,
            side=order_state.side,
            qty=order_state.qty,
            price=fill_price,
            status=order_state.state,
            order_id=order_state.order_id,
            reason=order_state.reason,
            raw={"filled_qty": order_state.filled_qty, "remaining_qty": order_state.remaining_qty()},
        )

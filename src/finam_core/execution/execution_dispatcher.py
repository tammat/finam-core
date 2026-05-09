# -*- coding: utf-8 -*-
"""
ExecutionDispatcher — единая точка маршрутизации исполнения.

Русский комментарий:
- paper остаётся режимом по умолчанию;
- real / real_dry_run идут только через RealExecutionEngine;
- прямой вызов orders_client из pipeline запрещён;
- категорию брокера здесь не используем.
"""

from __future__ import annotations

import os
from typing import Any
from finam_core.storage.postgres_logger import PostgresLogger
from finam_core.execution.oms_dispatch_guard import OmsDispatchGuard


class ExecutionDispatcher:
    def __init__(
        self,
        orders_client: Any | None = None,
        real_execution_engine: Any | None = None,
        paper_executor: Any | None = None,
        logger: Any | None = None,
        **kwargs,
    ) -> None:
        self.orders_client = orders_client
        self.real_execution_engine = real_execution_engine
        self.paper_executor = paper_executor
        self.logger = logger
        # Русский комментарий: журнал execution-событий не должен ломать route.
        self.execution_journal = logger if logger is not None else PostgresLogger()
        # Русский комментарий: OMS guard создаётся лениво, чтобы PAPER mode не зависел от БД.
        self._oms_dispatch_guard = None


    def _get_oms_dispatch_guard(self) -> OmsDispatchGuard:
        """Русский комментарий: лениво создаёт OMS guard для real/real_dry_run исполнения."""
        if self._oms_dispatch_guard is None:
            self._oms_dispatch_guard = OmsDispatchGuard()
        return self._oms_dispatch_guard


    def _log_execution_event_safe(
        self,
        *,
        event_type: str,
        symbol: str | None = None,
        side: str | None = None,
        qty: float | None = None,
        price: float | None = None,
        status: str | None = None,
        reason: str | None = None,
        order_id: str | None = None,
        raw_json: dict | None = None,
    ) -> None:
        """Русский комментарий: безопасный журнал dispatcher execution events."""
        try:
            if hasattr(self.execution_journal, "log_execution_event"):
                self.execution_journal.log_execution_event(
                    event_type=event_type,
                    symbol=symbol,
                    side=side,
                    qty=qty,
                    price=price,
                    status=status,
                    reason=reason,
                    order_id=order_id,
                    raw_json=raw_json or {},
                )
        except Exception as exc:
            print(f"DISPATCHER_EXECUTION_EVENT_LOG_FAILED event_type={event_type} error={exc}", flush=True)


    def execute(self, intent: dict, market_state: dict | None = None) -> Any:
        """Русский комментарий: основной route для pipeline."""
        mode = os.getenv("EXECUTION_MODE", "paper").strip().lower()

        if mode in {"real", "real_dry_run"}:
            if self.real_execution_engine is None:
                return {
                    "status": "REJECTED",
                    "reason": "real_execution_engine_not_configured",
                    "intent": intent,
                }

            oms_guard = self._get_oms_dispatch_guard()
            oms_decision = oms_guard.prepare(intent)

            if not oms_decision.allowed:
                print(
                    f"OMS_ORDER_DUPLICATE_BLOCK client_order_id={oms_decision.client_order_id} "
                    f"symbol={intent.get('symbol')} side={intent.get('side')} reason={oms_decision.reason}",
                    flush=True,
                )
                return {
                    "status": "REJECTED",
                    "reason": oms_decision.reason,
                    "client_order_id": oms_decision.client_order_id,
                    "intent": intent,
                }

            print(
                f"OMS_ORDER_JOURNAL_CREATED client_order_id={oms_decision.client_order_id} "
                f"symbol={intent.get('symbol')} side={intent.get('side')}",
                flush=True,
            )

            result = self.real_execution_engine.execute(
                intent=intent,
                market_state=market_state or {},
            )

            broker_order_id = None
            result_status = None

            if isinstance(result, dict):
                broker_order_id = result.get("order_id") or result.get("broker_order_id")
                result_status = result.get("status")
            else:
                broker_order_id = getattr(result, "order_id", None) or getattr(result, "broker_order_id", None)
                result_status = getattr(result, "status", None)

            if str(result_status or "").upper() in {"REJECTED", "ERROR", "FAILED"}:
                oms_guard.journal.update_status(
                    client_order_id=oms_decision.client_order_id,
                    status="REJECTED",
                    broker_order_id=str(broker_order_id) if broker_order_id else None,
                )
            else:
                oms_guard.mark_sent(
                    client_order_id=oms_decision.client_order_id,
                    broker_order_id=str(broker_order_id) if broker_order_id else None,
                )

            return result

        if self.paper_executor is not None:
            return self.paper_executor.execute(intent, market_state or {})

        return {
            "status": "SKIPPED",
            "reason": "paper_executor_not_configured",
            "intent": intent,
        }

    def place_limit_order(self, *, symbol: str, side: str, qty: float, limit_price: float, **kwargs) -> dict:
        """Русский комментарий: вспомогательный route для limit-заявок без категории брокера."""
        mode = os.getenv("EXECUTION_MODE", "paper").strip().lower()

        if mode in {"real", "real_dry_run"}:
            if self.orders_client is None or not hasattr(self.orders_client, "place_limit_order"):
                return {
                    "status": "REJECTED",
                    "reason": "orders_client_place_limit_order_not_configured",
                    "symbol": symbol,
                    "side": side,
                    "qty": float(qty),
                    "limit_price": float(limit_price),
                }

            result = self.orders_client.place_limit_order(
                symbol=symbol,
                side=side,
                qty=qty,
                limit_price=limit_price,
            )

            status = result.get("status") if isinstance(result, dict) else getattr(result, "status", None)
            reason = result.get("reason") if isinstance(result, dict) else getattr(result, "reason", None)
            order_id = result.get("order_id") if isinstance(result, dict) else getattr(result, "order_id", None)

            self._log_execution_event_safe(
                event_type="LIMIT_ORDER_RESULT",
                symbol=symbol,
                side=side,
                qty=qty,
                price=limit_price,
                status=status,
                reason=reason,
                order_id=order_id,
                raw_json={"result": result},
            )

            return result

        return {
            "status": "PAPER_LIMIT_SKIPPED",
            "symbol": symbol,
            "side": side,
            "qty": float(qty),
            "limit_price": float(limit_price),
        }

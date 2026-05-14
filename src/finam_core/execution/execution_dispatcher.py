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
from finam_core.futures.futures_access_gate import FuturesAccessGate
from finam_core.futures.futures_margin_guard import FuturesMarginGuard
from finam_core.risk.persistent_kill_switch import PersistentKillSwitch
from finam_core.events.event_store import EventStore
from finam_core.execution.fill_metadata_factory import FillMetadataFactory


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
        # Русский комментарий: futures gate создаётся лениво и блокирует real futures до разрешения.
        self._futures_access_gate = None
        # Русский комментарий: futures margin guard создаётся лениво перед real futures execution.
        self._futures_margin_guard = None
        # Русский комментарий: persistent kill switch блокирует real execution до любых broker/OMS действий.
        self._persistent_kill_switch = None
        # Русский комментарий: EventStore создаётся лениво и не должен ломать execution route.
        self._event_store = None


    def _get_oms_dispatch_guard(self) -> OmsDispatchGuard:
        """Русский комментарий: лениво создаёт OMS guard для real/real_dry_run исполнения."""
        if self._oms_dispatch_guard is None:
            self._oms_dispatch_guard = OmsDispatchGuard()
        return self._oms_dispatch_guard


    def _get_futures_access_gate(self) -> FuturesAccessGate:
        """Русский комментарий: лениво создаёт gate доступа к real futures."""
        if self._futures_access_gate is None:
            self._futures_access_gate = FuturesAccessGate()
        return self._futures_access_gate


    def _get_futures_margin_guard(self) -> FuturesMarginGuard:
        """Русский комментарий: лениво создаёт futures margin guard."""
        if self._futures_margin_guard is None:
            self._futures_margin_guard = FuturesMarginGuard()
        return self._futures_margin_guard


    def _get_persistent_kill_switch(self) -> PersistentKillSwitch:
        """Русский комментарий: лениво создаёт persistent kill switch."""
        if self._persistent_kill_switch is None:
            self._persistent_kill_switch = PersistentKillSwitch()
        return self._persistent_kill_switch


    def _get_event_store(self) -> EventStore:
        """Русский комментарий: лениво создаёт EventStore."""
        if self._event_store is None:
            self._event_store = EventStore()
        return self._event_store


    def _append_event_safe(
        self,
        *,
        event_type: str,
        aggregate_type: str = "execution",
        aggregate_id: str | None = None,
        source: str = "execution_dispatcher",
        payload: dict | None = None,
    ) -> None:
        """Русский комментарий: audit event не должен ломать торговый route."""
        try:
            store = self._get_event_store()
            store.append(
                event_type=event_type,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                source=source,
                payload=payload or {},
            )
        except Exception as exc:
            print(f"EVENT_STORE_APPEND_FAILED event_type={event_type} error={exc}", flush=True)


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

            kill_switch = self._get_persistent_kill_switch()
            if kill_switch.is_active(symbol=str(intent.get("symbol") or "")):
                state = kill_switch.get_state(scope="GLOBAL")
                if not state.active:
                    state = kill_switch.get_state(scope="SYMBOL", symbol=str(intent.get("symbol") or ""))

                print(
                    f"PERSISTENT_KILL_SWITCH_BLOCK symbol={intent.get('symbol')} "
                    f"scope={state.scope} reason={state.reason}",
                    flush=True,
                )
                self._append_event_safe(
                    event_type="EXECUTION_REJECTED",
                    aggregate_type="order",
                    aggregate_id=str(intent.get("client_order_id") or intent.get("symbol") or ""),
                    payload={
                        "reason": "persistent_kill_switch_active",
                        "kill_switch_reason": state.reason,
                        "symbol": intent.get("symbol"),
                        "intent": dict(intent),
                    },
                )
                return {
                    "status": "REJECTED",
                    "reason": "persistent_kill_switch_active",
                    "kill_switch_reason": state.reason,
                    "symbol": intent.get("symbol"),
                    "intent": intent,
                }

            futures_gate = self._get_futures_access_gate()
            futures_decision = futures_gate.check(
                symbol=str(intent.get("symbol") or ""),
                execution_mode=mode,
            )

            if not futures_decision.allowed:
                print(
                    f"FUTURES_ACCESS_BLOCK symbol={intent.get('symbol')} "
                    f"mode={mode} reason={futures_decision.reason}",
                    flush=True,
                )
                self._append_event_safe(
                    event_type="FUTURES_ACCESS_BLOCKED",
                    aggregate_type="order",
                    aggregate_id=str(intent.get("client_order_id") or intent.get("symbol") or ""),
                    payload={
                        "reason": futures_decision.reason,
                        "symbol": intent.get("symbol"),
                        "mode": mode,
                        "intent": dict(intent),
                    },
                )
                return {
                    "status": "REJECTED",
                    "reason": futures_decision.reason,
                    "symbol": intent.get("symbol"),
                    "intent": intent,
                }

            margin_guard = self._get_futures_margin_guard()
            margin_decision = margin_guard.check(
                symbol=str(intent.get("symbol") or ""),
                qty=float(intent.get("qty") or 0.0),
                equity=float(
                    intent.get("portfolio_equity")
                    or intent.get("equity")
                    or (market_state or {}).get("portfolio_equity")
                    or (market_state or {}).get("equity")
                    or os.getenv("PORTFOLIO_EQUITY", "0")
                ),
                used_margin_before=float(
                    intent.get("used_margin")
                    or (market_state or {}).get("used_margin")
                    or os.getenv("USED_MARGIN", "0")
                ),
            )

            if not margin_decision.allowed:
                print(
                    f"FUTURES_MARGIN_BLOCK symbol={intent.get('symbol')} "
                    f"qty={intent.get('qty')} reason={margin_decision.reason} "
                    f"required_margin={margin_decision.required_margin} "
                    f"util_after={margin_decision.margin_utilization_after:.4f}",
                    flush=True,
                )
                self._append_event_safe(
                    event_type="FUTURES_MARGIN_BLOCKED",
                    aggregate_type="order",
                    aggregate_id=str(intent.get("client_order_id") or intent.get("symbol") or ""),
                    payload={
                        "reason": margin_decision.reason,
                        "symbol": intent.get("symbol"),
                        "qty": intent.get("qty"),
                        "required_margin": margin_decision.required_margin,
                        "margin_utilization_after": margin_decision.margin_utilization_after,
                        "intent": dict(intent),
                    },
                )
                return {
                    "status": "REJECTED",
                    "reason": margin_decision.reason,
                    "symbol": intent.get("symbol"),
                    "required_margin": margin_decision.required_margin,
                    "margin_utilization_after": margin_decision.margin_utilization_after,
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
                self._append_event_safe(
                    event_type="ORDER_DUPLICATE_BLOCKED",
                    aggregate_type="order",
                    aggregate_id=oms_decision.client_order_id,
                    payload={
                        "reason": oms_decision.reason,
                        "symbol": intent.get("symbol"),
                        "side": intent.get("side"),
                        "intent": dict(intent),
                    },
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
            self._append_event_safe(
                event_type="ORDER_CREATED",
                aggregate_type="order",
                aggregate_id=oms_decision.client_order_id,
                payload={
                    "symbol": intent.get("symbol"),
                    "side": intent.get("side"),
                    "qty": intent.get("qty"),
                    "price": intent.get("price"),
                    "intent": dict(intent),
                },
            )

            result = self.real_execution_engine.execute(
                intent=intent,
                market_state=market_state or {},
            )

            # Русский комментарий: единая metadata-линия для REAL/DRY_RUN результата исполнения.
            FillMetadataFactory.attach(
                result,
                intent=intent,
                market_state=market_state or {},
                raw_fill=result,
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

            self._append_event_safe(
                event_type="ORDER_DISPATCH_RESULT",
                aggregate_type="order",
                aggregate_id=oms_decision.client_order_id,
                payload={
                    "symbol": intent.get("symbol"),
                    "side": intent.get("side"),
                    "broker_order_id": broker_order_id,
                    "status": result_status,
                    "result": result if isinstance(result, dict) else str(result),
                },
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

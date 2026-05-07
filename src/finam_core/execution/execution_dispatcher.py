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

            return self.real_execution_engine.execute(
                intent=intent,
                market_state=market_state or {},
            )

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

            return self.orders_client.place_limit_order(
                symbol=symbol,
                side=side,
                qty=qty,
                limit_price=limit_price,
            )

        return {
            "status": "PAPER_LIMIT_SKIPPED",
            "symbol": symbol,
            "side": side,
            "qty": float(qty),
            "limit_price": float(limit_price),
        }

# -*- coding: utf-8 -*-
"""
ExecutionDispatcher — единая точка маршрутизации заявок.

Русский комментарий:
- paper execution остаётся дефолтом;
- live execution разрешается только через EXECUTION_MODE=real;
- реальная отправка дополнительно защищена внутри FinamOrdersClient флагами:
  REAL_EXECUTION_ENABLED=1 и REAL_ORDER_CONFIRM=1.
"""

from __future__ import annotations

import os
from typing import Any


class ExecutionDispatcher:
    def __init__(self, paper_executor: Any, live_executor: Any, capabilities_gate: Any, logger: Any = None) -> None:
        self.paper_executor = paper_executor
        self.live_executor = live_executor
        self.capabilities_gate = capabilities_gate
        self.logger = logger

    def place_limit_order(self, *, symbol: str, side: str, qty: float, limit_price: float, instrument_type: str = "STOCK") -> dict:
        ok, reason = self.capabilities_gate.validate_order(
            instrument_type=instrument_type,
            side=side,
            qty=qty,
        )

        if not ok:
            result = {
                "status": "REJECTED",
                "symbol": symbol,
                "side": side,
                "qty": float(qty),
                "limit_price": float(limit_price),
                "reason": reason,
            }
            if self.logger and hasattr(self.logger, "log_rejected_order"):
                self.logger.log_rejected_order(result)
            return result

        mode = os.getenv("EXECUTION_MODE", "paper").lower()

        if mode == "real":
            return self.live_executor.place_limit_order(
                symbol=symbol,
                side=side,
                qty=qty,
                limit_price=limit_price,
            )

        return self.paper_executor.place_limit_order(
            symbol=symbol,
            side=side,
            qty=qty,
            limit_price=limit_price,
        )

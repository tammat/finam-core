# -*- coding: utf-8 -*-
"""
RealExecutionSafetyLayer — финальный предохранитель перед real order.

Русский комментарий: AI/strategy/risk не имеют права отправлять real order напрямую.
Перед real execution обязательно проверяются режим, инструмент, qty и duplicate guard.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class RealExecutionSafetyDecision:
    allowed: bool
    reason: str


class RealExecutionSafetyLayer:
    def __init__(self) -> None:
        self.execution_enabled = os.getenv("EXECUTION_ENABLED", "0") == "1"
        self.real_trading_enabled = os.getenv("REAL_TRADING_ENABLED", "0") == "1"
        self.real_stocks_only = os.getenv("REAL_STOCKS_ONLY", "1") == "1"
        self.max_qty = float(os.getenv("REAL_MAX_QTY", "1"))
        self.duplicate_ttl_sec = float(os.getenv("REAL_DUPLICATE_TTL_SEC", "30"))
        self._last_order_key: tuple[str, str] | None = None
        self._last_order_ts = 0.0

    def check(self, symbol: str, side: str, qty: float, execution_mode: str | None = None) -> RealExecutionSafetyDecision:
        mode = (execution_mode or os.getenv("EXECUTION_MODE", "paper")).strip().lower()
        symbol_value = (symbol or "").strip().upper()
        side_value = (side or "").strip().upper()
        qty_value = float(qty or 0.0)

        if mode not in ("real", "live"):
            return RealExecutionSafetyDecision(True, "NOT_REAL_MODE")

        if not self.execution_enabled:
            return RealExecutionSafetyDecision(False, "REAL_EXECUTION_DISABLED")

        if not self.real_trading_enabled:
            return RealExecutionSafetyDecision(False, "REAL_TRADING_DISABLED")

        if not symbol_value:
            return RealExecutionSafetyDecision(False, "REAL_EMPTY_SYMBOL")

        if side_value not in ("BUY", "SELL"):
            return RealExecutionSafetyDecision(False, "REAL_INVALID_SIDE")

        if qty_value <= 0:
            return RealExecutionSafetyDecision(False, "REAL_INVALID_QTY")

        if qty_value > self.max_qty:
            return RealExecutionSafetyDecision(False, "REAL_QTY_LIMIT_EXCEEDED")

        if self.real_stocks_only:
            if symbol_value.endswith("@RTSX"):
                return RealExecutionSafetyDecision(False, "REAL_FUTURES_BLOCKED")
            if not symbol_value.endswith("@MISX"):
                return RealExecutionSafetyDecision(False, "REAL_NON_MISX_BLOCKED")

        now = time.time()
        order_key = (symbol_value, side_value)
        if self._last_order_key == order_key and (now - self._last_order_ts) < self.duplicate_ttl_sec:
            return RealExecutionSafetyDecision(False, "REAL_DUPLICATE_ORDER_BLOCKED")

        self._last_order_key = order_key
        self._last_order_ts = now

        return RealExecutionSafetyDecision(True, "REAL_EXECUTION_SAFETY_OK")

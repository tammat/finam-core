# -*- coding: utf-8 -*-
"""
RealStockSafetyGate — предохранитель real-режима для акций.

Русский комментарий: слой запрещает real futures и разрешает real только для акций @MISX,
если включён REAL_STOCKS_ONLY=1.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RealStockSafetyDecision:
    allowed: bool
    reason: str


class RealStockSafetyGate:
    def __init__(self) -> None:
        self.real_stocks_only = os.getenv("REAL_STOCKS_ONLY", "1") == "1"

    def check(self, symbol: str, execution_mode: str | None = None) -> RealStockSafetyDecision:
        mode = (execution_mode or os.getenv("EXECUTION_MODE", "paper")).strip().lower()
        symbol_value = (symbol or "").strip().upper()

        if mode not in ("real", "live"):
            return RealStockSafetyDecision(True, "NOT_REAL_MODE")

        if not self.real_stocks_only:
            return RealStockSafetyDecision(True, "REAL_STOCKS_ONLY_DISABLED")

        if not symbol_value:
            return RealStockSafetyDecision(False, "REAL_STOCK_GATE_EMPTY_SYMBOL")

        if symbol_value.endswith("@RTSX"):
            return RealStockSafetyDecision(False, "REAL_STOCK_GATE_BLOCKED_FUTURES")

        if not symbol_value.endswith("@MISX"):
            return RealStockSafetyDecision(False, "REAL_STOCK_GATE_BLOCKED_NON_MISX")

        return RealStockSafetyDecision(True, "REAL_STOCK_GATE_ALLOWED_MISX_STOCK")

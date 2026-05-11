# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PositionMismatchDecision:
    allowed: bool
    reason: str
    symbol: str
    broker_qty: float
    local_qty: float
    diff: float


class PositionMismatchGate:
    def __init__(self, tolerance: float | None = None) -> None:
        self.tolerance = float(tolerance if tolerance is not None else os.getenv("POSITION_MISMATCH_TOLERANCE", "0.000001"))

    def check(self, symbol: str, broker_qty: float, local_qty: float) -> PositionMismatchDecision:
        diff = float(broker_qty or 0.0) - float(local_qty or 0.0)

        if abs(diff) > self.tolerance:
            return PositionMismatchDecision(False, "POSITION_MISMATCH_BLOCK", symbol, float(broker_qty), float(local_qty), diff)

        return PositionMismatchDecision(True, "POSITION_MATCH_OK", symbol, float(broker_qty), float(local_qty), diff)

# -*- coding: utf-8 -*-
"""
BrokerReconciliationEngine.
Русский комментарий: read-only сверка локальной позиции с брокерской.
Заявки не отправляет.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReconciliationResult:
    symbol: str
    local_qty: float
    broker_qty: float
    ok: bool
    reason: str


class BrokerReconciliationEngine:
    def __init__(self, qty_tolerance: float = 1e-9) -> None:
        self.qty_tolerance = float(qty_tolerance)

    def check_position(self, symbol: str, local_qty: float, broker_qty: float) -> ReconciliationResult:
        lq = float(local_qty or 0.0)
        bq = float(broker_qty or 0.0)

        diff = abs(lq - bq)
        ok = diff <= self.qty_tolerance

        return ReconciliationResult(
            symbol=str(symbol),
            local_qty=lq,
            broker_qty=bq,
            ok=ok,
            reason="RECONCILIATION_OK" if ok else "RECONCILIATION_MISMATCH",
        )

# -*- coding: utf-8 -*-
"""
PortfolioReconciliationRepair.

Русский комментарий:
Authoritative repair layer поверх read-only BrokerReconciliationEngine.
Сам заявки не отправляет. Основная задача — принять решение:
- можно торговать;
- нужен halt;
- можно синхронизировать локальную позицию с брокерской только при явном allow_repair=True.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioRepairDecision:
    symbol: str
    local_qty: float
    broker_qty: float
    status: str
    reason: str
    repaired_qty: float | None = None


class PortfolioReconciliationRepair:
    def __init__(self, qty_tolerance: float = 1e-9) -> None:
        self.qty_tolerance = float(qty_tolerance)

    def evaluate(
        self,
        *,
        symbol: str,
        local_qty: float,
        broker_qty: float,
        allow_repair: bool = False,
    ) -> PortfolioRepairDecision:
        lq = float(local_qty or 0.0)
        bq = float(broker_qty or 0.0)

        if abs(lq - bq) <= self.qty_tolerance:
            return PortfolioRepairDecision(
                symbol=str(symbol),
                local_qty=lq,
                broker_qty=bq,
                status="OK",
                reason="portfolio_reconciliation_ok",
                repaired_qty=lq,
            )

        if not allow_repair:
            return PortfolioRepairDecision(
                symbol=str(symbol),
                local_qty=lq,
                broker_qty=bq,
                status="HALT_REQUIRED",
                reason=f"portfolio_reconciliation_mismatch:local={lq}:broker={bq}",
                repaired_qty=None,
            )

        return PortfolioRepairDecision(
            symbol=str(symbol),
            local_qty=lq,
            broker_qty=bq,
            status="REPAIRED",
            reason=f"portfolio_reconciliation_repaired:local={lq}:broker={bq}",
            repaired_qty=bq,
        )

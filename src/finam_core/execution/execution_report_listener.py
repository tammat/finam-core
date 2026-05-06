# -*- coding: utf-8 -*-
"""
ExecutionReportListener.
Русский комментарий: принимает broker execution reports и применяет fills к RealExecutionEngine.
Заявки не отправляет.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExecutionReport:
    order_id: str
    symbol: str
    side: str
    status: str
    fill_qty: float = 0.0
    fill_price: float = 0.0
    raw: dict | None = None


class ExecutionReportListener:
    def __init__(self, real_execution_engine: Any) -> None:
        self.real_execution_engine = real_execution_engine

    def normalize(self, report: dict) -> ExecutionReport:
        order_id = str(
            report.get("order_id")
            or report.get("broker_order_id")
            or report.get("transaction_id")
            or ""
        )

        symbol = str(report.get("symbol") or report.get("ticker") or "")
        side = str(report.get("side") or "").upper()
        status = str(report.get("status") or report.get("state") or "").upper()

        fill_qty = float(
            report.get("fill_qty")
            or report.get("filled_qty")
            or report.get("last_qty")
            or 0.0
        )

        fill_price = float(
            report.get("fill_price")
            or report.get("price")
            or report.get("last_price")
            or 0.0
        )

        return ExecutionReport(
            order_id=order_id,
            symbol=symbol,
            side=side,
            status=status,
            fill_qty=fill_qty,
            fill_price=fill_price,
            raw=report,
        )

    def on_report(self, report: dict):
        normalized = self.normalize(report)

        if not normalized.order_id:
            return {
                "status": "REJECTED",
                "reason": "execution_report_missing_order_id",
                "raw": report,
            }

        if normalized.status in ("PARTIAL_FILLED", "PARTIALLY_FILLED", "FILLED"):
            if normalized.fill_qty <= 0:
                return {
                    "status": "REJECTED",
                    "reason": "execution_report_missing_fill_qty",
                    "order_id": normalized.order_id,
                }

            if normalized.fill_price <= 0:
                return {
                    "status": "REJECTED",
                    "reason": "execution_report_missing_fill_price",
                    "order_id": normalized.order_id,
                }

            return self.real_execution_engine.on_fill(
                normalized.order_id,
                normalized.fill_qty,
                normalized.fill_price,
            )

        return {
            "status": "IGNORED",
            "reason": f"execution_report_status_not_fill:{normalized.status}",
            "order_id": normalized.order_id,
        }

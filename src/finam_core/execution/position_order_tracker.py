# -*- coding: utf-8 -*-
"""
PositionOrderTracker.
Русский комментарий: сопоставляет брокерские позиции и активные заявки.
Заявки не отправляет.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PositionOrderState:
    symbol: str
    position_qty: float
    stop_qty: float
    take_qty: float
    protected: bool
    protection_gap_qty: float


class PositionOrderTracker:
    def evaluate(self, symbol: str, position_qty: float, orders: list[dict]) -> PositionOrderState:
        qty = abs(float(position_qty or 0.0))

        stop_qty = 0.0
        take_qty = 0.0

        for order in orders:
            if order.get("symbol") != symbol:
                continue

            order_type = str(order.get("type", "")).upper()
            order_qty = abs(float(order.get("qty", 0.0) or 0.0))

            if order_type in ("STOP", "STOP_LIMIT"):
                stop_qty += order_qty

            if order_type in ("LIMIT", "TAKE_PROFIT"):
                take_qty += order_qty

        protected = qty > 0 and stop_qty >= qty
        gap = max(0.0, qty - stop_qty)

        return PositionOrderState(
            symbol=symbol,
            position_qty=float(position_qty or 0.0),
            stop_qty=stop_qty,
            take_qty=take_qty,
            protected=protected,
            protection_gap_qty=gap,
        )

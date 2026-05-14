# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ManualPositionPnl:
    symbol: str
    qty: float
    average_price: float
    current_price: float
    price_delta: float
    pnl_pct: float
    status: str


def analyze_position(
    *,
    symbol: str,
    qty: float,
    average_price: Optional[float],
    current_price: Optional[float],
) -> Optional[ManualPositionPnl]:
    if average_price is None or current_price is None:
        return None

    if average_price == 0:
        return None

    price_delta = current_price - average_price
    pnl_pct = (current_price / average_price - 1.0) * 100.0

    if pnl_pct > 0.05:
        status = "PROFIT"
    elif pnl_pct < -0.05:
        status = "LOSS"
    else:
        status = "FLAT"

    return ManualPositionPnl(
        symbol=symbol,
        qty=float(qty),
        average_price=float(average_price),
        current_price=float(current_price),
        price_delta=price_delta,
        pnl_pct=pnl_pct,
        status=status,
    )

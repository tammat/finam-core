# -*- coding: utf-8 -*-
"""
Комиссии и налоговый резерв для paper/live accounting.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class FeeTaxResult:
    broker_fee: float
    exchange_fee: float
    tax_reserve: float

    @property
    def total(self) -> float:
        return self.broker_fee + self.exchange_fee + self.tax_reserve


class FeeTaxModel:
    def __init__(self) -> None:
        self.broker_rate = float(os.getenv("BROKER_FEE_RATE", "0.0"))
        self.exchange_rate = float(os.getenv("EXCHANGE_FEE_RATE", "0.0"))
        self.min_broker_fee = float(os.getenv("MIN_BROKER_FEE", "0.0"))
        self.tax_rate = float(os.getenv("TAX_RESERVE_RATE", "0.13"))

    def trade_fees(self, trade_value: float) -> FeeTaxResult:
        value = abs(float(trade_value or 0.0))
        broker_fee = max(value * self.broker_rate, self.min_broker_fee) if value > 0 else 0.0
        exchange_fee = value * self.exchange_rate
        return FeeTaxResult(broker_fee=broker_fee, exchange_fee=exchange_fee, tax_reserve=0.0)

    def tax_on_realized_profit(self, realized_pnl: float) -> FeeTaxResult:
        pnl = float(realized_pnl or 0.0)
        tax = max(pnl, 0.0) * self.tax_rate
        return FeeTaxResult(broker_fee=0.0, exchange_fee=0.0, tax_reserve=tax)

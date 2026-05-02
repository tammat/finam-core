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

    def commission(self, symbol: str, qty: float, price: float) -> float:
        # простой тариф (пример)
        rate = 0.0005  # 0.05%
        return abs(qty * price) * rate

    class FeeTaxModel:

        def __init__(self):
            self.tax_base_year = 0.0  # накопленная прибыль за год

        def commission(self, symbol: str, qty: float, price: float) -> float:
            rate = 0.0005  # 0.05%
            return abs(qty * price) * rate

        def tax(self, realized_pnl: float) -> float:
            """
            Налог РФ:
            - 13% до 5 млн
            - 15% сверх
            """
            if realized_pnl <= 0:
                return 0.0

            tax = 0.0

            remaining = realized_pnl
            threshold = 5_000_000 - self.tax_base_year

            # часть до 5 млн
            if threshold > 0:
                part_13 = min(remaining, threshold)
                tax += part_13 * 0.13
                remaining -= part_13
                self.tax_base_year += part_13

            # всё остальное — 15%
            if remaining > 0:
                tax += remaining * 0.15
                self.tax_base_year += remaining

            return tax
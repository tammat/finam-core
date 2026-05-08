# -*- coding: utf-8 -*-
from __future__ import annotations

from finam_core.instruments.contract_specs import ContractSpecRegistry


class FuturesPnlCalculator:
    def __init__(self, registry: ContractSpecRegistry | None = None) -> None:
        self.registry = registry or ContractSpecRegistry()

    def pnl(self, *, symbol: str, side: str, entry: float, exit: float, qty: float) -> float:
        spec = self.registry.get(symbol)
        side = str(side).upper()

        if side == "BUY":
            price_delta = float(exit) - float(entry)
        else:
            price_delta = float(entry) - float(exit)

        ticks = price_delta / spec.min_price_step
        return round(ticks * spec.step_value * float(qty), 4)

    def risk_money(self, *, symbol: str, entry: float, stop: float, qty: float) -> float:
        spec = self.registry.get(symbol)
        ticks = abs(float(entry) - float(stop)) / spec.min_price_step
        return round(ticks * spec.step_value * float(qty), 4)

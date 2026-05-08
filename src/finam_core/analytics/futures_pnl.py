# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ContractSpec:
    symbol_prefix: str
    point_value: float = 1.0
    currency: str = "RUB"


class FuturesPnlCalculator:
    """
    Русский комментарий:
    Денежный P&L фьючерса = изменение цены * qty * point_value.
    point_value задаём через ENV, чтобы не хардкодить спецификации контрактов.
    """

    def __init__(self) -> None:
        self.specs = self._load_specs()

    def _load_specs(self) -> dict[str, ContractSpec]:
        specs: dict[str, ContractSpec] = {}

        raw = os.getenv("FUTURES_POINT_VALUES_JSON", "").strip()
        if raw:
            data = json.loads(raw)
            for prefix, cfg in data.items():
                specs[prefix.upper()] = ContractSpec(
                    symbol_prefix=prefix.upper(),
                    point_value=float(cfg.get("point_value", 1.0)),
                    currency=str(cfg.get("currency", "RUB")),
                )

        for prefix in ("BR", "NG", "SI", "RI", "MX"):
            env_key = f"FUTURES_POINT_VALUE_{prefix}"
            if os.getenv(env_key):
                specs[prefix] = ContractSpec(
                    symbol_prefix=prefix,
                    point_value=float(os.getenv(env_key, "1")),
                    currency=os.getenv(f"FUTURES_CURRENCY_{prefix}", "RUB"),
                )

        return specs

    def spec_for(self, symbol: str) -> ContractSpec:
        base = str(symbol or "").upper().split("@", 1)[0]
        for prefix, spec in self.specs.items():
            if base.startswith(prefix):
                return spec
        return ContractSpec(symbol_prefix=base, point_value=1.0, currency="RUB")

    def pnl(self, *, symbol: str, side: str, entry: float, exit: float, qty: float) -> float:
        spec = self.spec_for(symbol)
        side = str(side).upper()

        if side == "BUY":
            points = float(exit) - float(entry)
        else:
            points = float(entry) - float(exit)

        return round(points * float(qty) * float(spec.point_value), 4)

    def risk_money(self, *, symbol: str, side: str, entry: float, stop: float, qty: float) -> float:
        spec = self.spec_for(symbol)
        risk_points = abs(float(entry) - float(stop))
        return round(risk_points * float(qty) * float(spec.point_value), 4)

# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ContractSpec:
    prefix: str
    min_price_step: float
    step_value: float
    currency: str = "RUB"


class ContractSpecRegistry:
    def __init__(self) -> None:
        self.specs = self._load_specs()

    def _load_specs(self) -> dict[str, ContractSpec]:
        specs = {
            "BR": ContractSpec("BR", 0.01, float(os.getenv("FUTURES_SPEC_BR_STEP_VALUE", "10")), "RUB"),
            "SI": ContractSpec("SI", 1.0, float(os.getenv("FUTURES_SPEC_SI_STEP_VALUE", "1")), "RUB"),
            "NG": ContractSpec("NG", 0.001, float(os.getenv("FUTURES_SPEC_NG_STEP_VALUE", "1")), "RUB"),
            "RI": ContractSpec("RI", 10.0, float(os.getenv("FUTURES_SPEC_RI_STEP_VALUE", "10")), "RUB"),
            "MX": ContractSpec("MX", 0.25, float(os.getenv("FUTURES_SPEC_MX_STEP_VALUE", "1")), "RUB"),
        }

        raw = os.getenv("FUTURES_CONTRACT_SPECS_JSON", "").strip()
        if raw:
            data = json.loads(raw)
            for prefix, cfg in data.items():
                specs[prefix.upper()] = ContractSpec(
                    prefix=prefix.upper(),
                    min_price_step=float(cfg["min_price_step"]),
                    step_value=float(cfg["step_value"]),
                    currency=str(cfg.get("currency", "RUB")),
                )

        return specs

    def get(self, symbol: str) -> ContractSpec:
        base = str(symbol or "").upper().split("@", 1)[0]
        for prefix, spec in self.specs.items():
            if base.startswith(prefix):
                return spec
        return ContractSpec(base, 1.0, 1.0, "RUB")

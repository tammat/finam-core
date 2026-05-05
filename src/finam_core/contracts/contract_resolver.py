# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ContractSpec:
    root: str
    active_symbol: str
    next_symbol: str | None = None
    mic: str = "RTSX"


class ContractResolver:
    """Русский комментарий: единая точка выбора активного фьючерсного контракта."""

    def __init__(self) -> None:
        self._defaults = {
            "BR": ContractSpec(
                root="BR",
                active_symbol=os.getenv("BR_CONTRACT", "BRM6@RTSX"),
                next_symbol=os.getenv("BR_NEXT_CONTRACT", "BRN6@RTSX"),
            ),
            "NG": ContractSpec(
                root="NG",
                active_symbol=os.getenv("NG_CONTRACT", "NGK6@RTSX"),
                next_symbol=os.getenv("NG_NEXT_CONTRACT", "NGN6@RTSX"),
            ),
            "USDRUB": ContractSpec(
                root="USDRUB",
                active_symbol=os.getenv("USDRUB_CONTRACT", "USDRUBF@RTSX"),
                next_symbol=os.getenv("USDRUB_NEXT_CONTRACT", ""),
            ),
        }

    def resolve(self, root: str) -> str:
        key = str(root or "").upper()
        if key not in self._defaults:
            raise KeyError(f"Unknown contract root: {root}")
        return self._defaults[key].active_symbol

    def next_contract(self, root: str) -> str | None:
        key = str(root or "").upper()
        if key not in self._defaults:
            raise KeyError(f"Unknown contract root: {root}")
        value = self._defaults[key].next_symbol
        return value or None

    def all_active(self) -> dict[str, str]:
        return {root: spec.active_symbol for root, spec in self._defaults.items()}

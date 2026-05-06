# -*- coding: utf-8 -*-
"""
PositionIntentClassifier.
Русский комментарий: классифицирует реальные позиции по горизонту управления.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PositionIntent:
    symbol: str
    horizon: str
    allow_intraday_exit: bool
    allow_trailing: bool
    allow_new_buy: bool


class PositionIntentClassifier:
    def __init__(self) -> None:
        self.rules = {
            # Русский комментарий: инструменты активной внутридневной торговли.
            "BRM6@RTSX": "intraday",
            "NGK6@RTSX": "intraday",
            "USDRUBF@RTSX": "intraday",

            # Русский комментарий: среднесрочные позиции, не закрывать intraday-логикой.
            "PLZL@MISX": "swing",
            "LKOH@MISX": "swing",
            "NVTK@MISX": "swing",
            "X5@MISX": "swing",
            "SBERP@MISX": "swing",
            "OZON@MISX": "swing",
            "T@MISX": "swing",
            "SFIN@MISX": "swing",

            # Русский комментарий: долгосрочные/облигационные позиции — не трогать торговой логикой.
            "EUTR@MISX": "long_term",
        }

    def classify(self, symbol: str) -> PositionIntent:
        sym = str(symbol or "")
        horizon = self.rules.get(sym, "swing")

        return PositionIntent(
            symbol=sym,
            horizon=horizon,
            allow_intraday_exit=horizon == "intraday",
            allow_trailing=horizon in ("intraday", "swing"),
            allow_new_buy=horizon != "long_term",
        )

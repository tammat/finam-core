# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SymbolLimit:
    symbol: str
    max_abs_position: float
    source: str


def env_symbol_key(symbol: str) -> str:
    return (
        symbol.upper()
        .replace("@", "_")
        .replace("-", "_")
        .replace(".", "_")
        .replace("/", "_")
    )


class FinamLimitsAdapter:
    """
    Русский комментарий:
    Источник лимитов по инструментам.
    Сейчас безопасный режим: .env fallback.
    Реальные лимиты Финама можно подключить позже через portfolio/account API,
    не меняя интерфейс get_symbol_limit().
    """

    def __init__(self) -> None:
        self.default_max_abs_position = float(os.getenv("MAX_ABS_POSITION_DEFAULT", "1"))

    def get_symbol_limit(self, symbol: str) -> SymbolLimit:
        key = f"MAX_ABS_POSITION_{env_symbol_key(symbol)}"
        if os.getenv(key):
            return SymbolLimit(
                symbol=symbol,
                max_abs_position=float(os.getenv(key, "1")),
                source=f"env:{key}",
            )

        return SymbolLimit(
            symbol=symbol,
            max_abs_position=self.default_max_abs_position,
            source="env:MAX_ABS_POSITION_DEFAULT",
        )

    def get_limits(self, symbols: list[str]) -> dict[str, SymbolLimit]:
        return {symbol: self.get_symbol_limit(symbol) for symbol in symbols}

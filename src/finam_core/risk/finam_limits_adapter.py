# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SymbolLimit:
    symbol: str
    max_abs_position: float
    source: str
    current_position: float = 0.0


def env_symbol_key(symbol: str) -> str:
    return (
        symbol.upper()
        .replace("@", "_")
        .replace("-", "_")
        .replace(".", "_")
        .replace("/", "_")
    )


def split_symbol(symbol: str) -> tuple[str, str]:
    if "@" in symbol:
        a, b = symbol.split("@", 1)
        return a, b
    return symbol, ""


class FinamLimitsAdapter:
    """
    Русский комментарий:
    1. Пытаемся читать текущие позиции из Finam client.
    2. Лимит max_abs_position берём из env как cap.
    3. Если API недоступен — полностью fallback на env.
    """

    def __init__(self) -> None:
        self.default_max_abs_position = float(os.getenv("MAX_ABS_POSITION_DEFAULT", "1"))
        self._positions_cache: dict[str, float] | None = None
        self._positions_source: str = "not_loaded"

    def _env_limit(self, symbol: str) -> tuple[float, str]:
        key = f"MAX_ABS_POSITION_{env_symbol_key(symbol)}"
        if os.getenv(key):
            return float(os.getenv(key, "1")), f"env:{key}"
        return self.default_max_abs_position, "env:MAX_ABS_POSITION_DEFAULT"

    def _load_finam_positions(self) -> dict[str, float]:
        if self._positions_cache is not None:
            return self._positions_cache

        try:
            from finam_core.infra.finam.client import FinamClient  # type: ignore

            client = FinamClient()
            positions = client.get_positions()
            out: dict[str, float] = {}

            for pos in positions:
                raw_symbol = str(pos.get("symbol", "") or "")
                mic = str(pos.get("mic", "") or "")
                qty = float(pos.get("qty", 0.0) or 0.0)

                full = f"{raw_symbol}@{mic}" if mic else raw_symbol
                if full:
                    out[full] = qty
                if raw_symbol:
                    out[raw_symbol] = qty

            self._positions_cache = out
            self._positions_source = "finam_api"
            return out

        except Exception as exc:
            self._positions_cache = {}
            self._positions_source = f"finam_api_unavailable:{type(exc).__name__}"
            return {}

    def get_current_position(self, symbol: str) -> tuple[float, str]:
        positions = self._load_finam_positions()
        base, _mic = split_symbol(symbol)
        if symbol in positions:
            return float(positions[symbol]), self._positions_source
        if base in positions:
            return float(positions[base]), self._positions_source
        return 0.0, self._positions_source

    def get_symbol_limit(self, symbol: str) -> SymbolLimit:
        env_limit, env_source = self._env_limit(symbol)
        current_position, pos_source = self.get_current_position(symbol)

        source = f"{pos_source}+{env_source}"
        return SymbolLimit(
            symbol=symbol,
            max_abs_position=env_limit,
            source=source,
            current_position=current_position,
        )

    def get_limits(self, symbols: list[str]) -> dict[str, SymbolLimit]:
        return {symbol: self.get_symbol_limit(symbol) for symbol in symbols}

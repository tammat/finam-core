from __future__ import annotations


def map_symbol_to_strategy(symbol: str) -> str:
    value = str(symbol).strip().upper()

    if value.startswith("BR"):
        return "br_conservative_breakout"

    if value.startswith("NG"):
        return "ng_volatility_breakout"

    if value.endswith("@MISX"):
        return "strategy_stack"

    if value.endswith("@RTSX"):
        return "futures_strategy_stack"

    return "strategy_stack"

from __future__ import annotations


def normalize_position_symbol(symbol: str) -> str:
    value = str(symbol).strip().upper()

    if not value:
        return ""

    if "@" in value:
        return value

    if value.startswith(("BR", "NG")) and any(ch.isdigit() for ch in value):
        return f"{value}@RTSX"

    return f"{value}@MISX"

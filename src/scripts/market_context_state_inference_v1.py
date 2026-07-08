from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def to_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def infer_volume_state(row: dict[str, Any] | None) -> str:
    if not row:
        return "UNKNOWN"

    for key in ("volume", "avg_volume", "turnover", "trade_value", "value", "amount"):
        value = to_decimal(row.get(key))
        if value is None:
            continue
        if value > 0:
            return "KNOWN"

    return "UNKNOWN"


def infer_liquidity_state(row: dict[str, Any] | None) -> str:
    if not row:
        return "UNKNOWN"

    explicit = infer_volume_state(row)
    if explicit != "UNKNOWN":
        return "KNOWN"

    for key in ("liquidity", "bid", "ask", "last", "close"):
        value = to_decimal(row.get(key))
        if value is not None and value > 0:
            return "KNOWN"

    return "UNKNOWN"


def infer_spread_state(row: dict[str, Any] | None) -> str:
    if not row:
        return "UNKNOWN"

    bid = to_decimal(row.get("bid"))
    ask = to_decimal(row.get("ask"))

    if bid is not None and ask is not None and bid > 0 and ask > 0:
        if ask >= bid:
            return "KNOWN"

    for key in ("spread", "bid_ask_spread", "spread_value"):
        value = to_decimal(row.get(key))
        if value is not None:
            return "KNOWN"

    return "UNKNOWN"

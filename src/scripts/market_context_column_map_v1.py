from __future__ import annotations

from typing import Any


COLUMN_MAP: dict[str, tuple[str, ...]] = {
    "regime": (
        "regime_code",
        "regime",
        "market_regime",
        "state",
        "regime_state",
    ),
    "volatility": (
        "volatility_state",
        "vol_state",
        "atr_state",
        "volatility",
        "atr_pct_state",
        "range_state",
    ),
    "liquidity": (
        "liquidity_state",
        "liq_state",
        "liquidity",
        "volume_state",
        "volume_quality",
        "turnover_state",
    ),
    "volume": (
        "volume_state",
        "volume_quality",
        "volume_regime",
        "volume",
        "turnover_state",
        "trade_value_state",
    ),
    "spread": (
        "spread_state",
        "spread_quality",
        "spread_regime",
        "spread",
        "bid_ask_spread_state",
    ),
    "session": (
        "session_state",
        "event_type",
        "calendar_state",
        "session",
        "market_session",
    ),
}


def read_mapped_value(row: dict[str, Any] | None, field: str, default: str = "UNKNOWN") -> str:
    if not row:
        return default

    for column in COLUMN_MAP.get(field, ()):
        if column in row and row[column] not in (None, ""):
            return str(row[column]).upper()

    return default

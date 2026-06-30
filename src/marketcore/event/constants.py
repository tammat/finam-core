from __future__ import annotations

from typing import Final

DEFAULT_EVENT_VERSION: Final[str] = "v1"
DEFAULT_EVENT_PAYLOAD_SQL: Final[str] = "'{}'::jsonb"

EVENT_TYPES: Final[tuple[str, ...]] = (
    "BAR_EVENT",
    "QUOTE_EVENT",
    "TRADE_TICK_EVENT",
    "DATA_QUALITY_EVENT",
    "CORRECTION_EVENT",
)

EVENT_GRANULARITY: Final[tuple[str, ...]] = (
    "TICK",
    "QUOTE",
    "BAR",
    "DAILY",
    "SESSION",
)

SOURCE_SYSTEM_TYPES: Final[tuple[str, ...]] = (
    "BROKER",
    "EXCHANGE",
    "DATA_VENDOR",
    "CSV",
    "BACKTEST",
    "SIMULATION",
)

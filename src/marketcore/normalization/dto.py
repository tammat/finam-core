from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class CanonicalMarketBarDTO:
    source_system_code: str
    source_key: str
    symbol_code: str
    timeframe_code: str
    event_time: datetime
    source_time: datetime
    received_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    payload: dict[str, Any]

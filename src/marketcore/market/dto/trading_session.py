from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TradingSessionDTO:
    session_code: str
    timezone: str
    open_time: str
    close_time: str
    has_auction: bool
    has_evening_session: bool
    is_weekend_trading_allowed: bool
    source_version: str

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from .base import SessionHours, TradingSession


@dataclass(frozen=True)
class CryptoSession(TradingSession):
    tz: ZoneInfo = ZoneInfo("UTC")
    hours: SessionHours = SessionHours(0, 0, 23, 59)

    def is_trading_day(self, now: datetime) -> bool:
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        return True

    def is_open(self, now: datetime) -> bool:
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        return True

    def next_open(self, now: datetime) -> datetime:
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        return now.astimezone(self.tz)

    def next_close(self, now: datetime) -> datetime:
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        n = now.astimezone(self.tz)
        return n.replace(hour=23, minute=59, second=0, microsecond=0)
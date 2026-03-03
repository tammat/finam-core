from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .base import SessionHours, TradingSession


@dataclass(frozen=True)
class CmeSession(TradingSession):
    """
    Placeholder only.
    Real CME hours vary by product and include maintenance breaks.
    """

    tz: ZoneInfo = ZoneInfo("America/Chicago")
    hours: SessionHours = SessionHours(0, 0, 23, 59)

    def _to_local(self, now: datetime) -> datetime:
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        return now.astimezone(self.tz)

    def is_trading_day(self, now: datetime) -> bool:
        n = self._to_local(now)
        return n.weekday() < 5  # Mon-Fri

    def is_open(self, now: datetime) -> bool:
        return self.is_trading_day(now)

    def next_open(self, now: datetime) -> datetime:
        n = self._to_local(now)
        if self.is_open(n):
            return n
        cur = n.replace(hour=0, minute=0, second=0, microsecond=0)
        while True:
            cur = cur + timedelta(days=1)
            if cur.weekday() < 5:
                return cur

    def next_close(self, now: datetime) -> datetime:
        n = self._to_local(now)
        return n.replace(hour=23, minute=59, second=0, microsecond=0)
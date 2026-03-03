from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .base import SessionHours, TradingSession

TZ_MOSCOW = ZoneInfo("Europe/Moscow")


@dataclass(frozen=True)
class MoexSession(TradingSession):
    """
    Platform assumption (per your requirement):
      - 7 days/week trading
      - 10:00–19:00 MSK
    Holidays/short sessions not modeled.
    """

    tz: ZoneInfo = TZ_MOSCOW
    hours: SessionHours = SessionHours(10, 0, 19, 0)

    def _to_local(self, now: datetime) -> datetime:
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        return now.astimezone(self.tz)

    def is_trading_day(self, now: datetime) -> bool:
        _ = self._to_local(now)
        return True

    def is_open(self, now: datetime) -> bool:
        n = self._to_local(now)
        open_dt = n.replace(hour=self.hours.open_hour, minute=self.hours.open_minute, second=0, microsecond=0)
        close_dt = n.replace(hour=self.hours.close_hour, minute=self.hours.close_minute, second=0, microsecond=0)
        return open_dt <= n < close_dt

    def next_open(self, now: datetime) -> datetime:
        n = self._to_local(now)

        open_dt = n.replace(hour=self.hours.open_hour, minute=self.hours.open_minute, second=0, microsecond=0)
        close_dt = n.replace(hour=self.hours.close_hour, minute=self.hours.close_minute, second=0, microsecond=0)

        # if already open -> now (platform convention)
        if open_dt <= n < close_dt:
            return n

        # before open -> today's open
        if n < open_dt:
            return open_dt

        # after close -> next day open (timedelta is month/year safe)
        next_day = (open_dt + timedelta(days=1)).date()
        return datetime(next_day.year, next_day.month, next_day.day, self.hours.open_hour, self.hours.open_minute, tzinfo=self.tz)

    def next_close(self, now: datetime) -> datetime:
        n = self._to_local(now)

        open_dt = n.replace(hour=self.hours.open_hour, minute=self.hours.open_minute, second=0, microsecond=0)
        close_dt = n.replace(hour=self.hours.close_hour, minute=self.hours.close_minute, second=0, microsecond=0)

        if n < open_dt:
            return close_dt
        if open_dt <= n < close_dt:
            return close_dt

        next_day = (close_dt + timedelta(days=1)).date()
        return datetime(next_day.year, next_day.month, next_day.day, self.hours.close_hour, self.hours.close_minute, tzinfo=self.tz)
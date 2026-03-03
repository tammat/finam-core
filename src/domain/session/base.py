from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class SessionHours:
    open_hour: int
    open_minute: int
    close_hour: int
    close_minute: int


class TradingSession(ABC):
    """
    All datetimes must be timezone-aware.
    Convention:
      - next_open(): if currently open -> return now (do not wait)
      - next_close(): if currently open -> return today's close
    """

    tz: ZoneInfo
    hours: SessionHours

    @abstractmethod
    def is_trading_day(self, now: datetime) -> bool: ...

    @abstractmethod
    def is_open(self, now: datetime) -> bool: ...

    @abstractmethod
    def next_open(self, now: datetime) -> datetime: ...

    @abstractmethod
    def next_close(self, now: datetime) -> datetime: ...
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


UTC = ZoneInfo("UTC")
MSK = ZoneInfo("Europe/Moscow")


class MarketSessionCalendar:
    """Русский комментарий: исторический календарь торговых сессий для анализа market_bars."""

    def is_open(self, *, symbol: str, ts: datetime) -> bool:
        symbol_upper = str(symbol or "").upper()

        if "@RTSX" in symbol_upper:
            return self._is_forts_open(ts)

        if "@MISX" in symbol_upper:
            return self._is_stock_open(ts)

        return False

    def has_open_time_between(
        self,
        *,
        symbol: str,
        start_ts: datetime,
        end_ts: datetime,
        step_minutes: int = 5,
    ) -> bool:
        start = self._to_utc(start_ts)
        end = self._to_utc(end_ts)

        if end <= start:
            return False

        # Русский комментарий: короткие сделки могут длиться меньше одного timeframe.
        # Поэтому сначала проверяем границы и середину интервала.
        if self.is_open(symbol=symbol, ts=start):
            return True

        if self.is_open(symbol=symbol, ts=end):
            return True

        midpoint = start + (end - start) / 2
        if self.is_open(symbol=symbol, ts=midpoint):
            return True

        step = timedelta(minutes=max(1, int(step_minutes)))
        current = start + step

        while current < end:
            if self.is_open(symbol=symbol, ts=current):
                return True
            current += step

        return False

    def _to_utc(self, ts: datetime) -> datetime:
        if ts.tzinfo is None:
            return ts.replace(tzinfo=UTC)
        return ts.astimezone(UTC)

    def _to_msk(self, ts: datetime) -> datetime:
        return self._to_utc(ts).astimezone(MSK)

    def _minute_of_day(self, ts: datetime) -> int:
        return ts.hour * 60 + ts.minute

    def _is_forts_open(self, ts: datetime) -> bool:
        msk = self._to_msk(ts)

        if msk.weekday() in (5, 6):
            return False

        minute = self._minute_of_day(msk)
        return 9 * 60 <= minute < 23 * 60 + 50

    def _is_stock_open(self, ts: datetime) -> bool:
        msk = self._to_msk(ts)

        if msk.weekday() in (5, 6):
            return False

        minute = self._minute_of_day(msk)
        return 6 * 60 + 50 <= minute < 23 * 60 + 50

# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


class SessionManager:
    """Русский комментарий: определяет торговую фазу MOEX для PAPER/live-paper gate."""

    def __init__(self, market: str = "FORTS") -> None:
        self.market = str(market or "FORTS").upper()

    def get_regime(
        self,
        symbol: str | None = None,
        *,
        market_data_live: bool = False,
        now: datetime | None = None,
    ):
        now = now or datetime.now(ZoneInfo("Europe/Moscow"))
        h = now.hour
        m = now.minute

        # Русский комментарий: на выходных отдельное окно торгов 10:00–19:00 МСК.
        if self._is_weekend(now):
            return self._weekend_session(now, market_data_live=market_data_live)

        market = self.market
        if symbol:
            symbol_upper = str(symbol).upper()
            if "@MISX" in symbol_upper:
                market = "STOCK"
            elif "@RTSX" in symbol_upper:
                market = "FORTS"

        if market == "FORTS":
            return self._forts_session(h, m)

        return self._stock_session(h, m)

    def _minute_of_day(self, h: int, m: int) -> int:
        return int(h) * 60 + int(m)

    def _is_weekend(self, now: datetime | None = None) -> bool:
        """Русский комментарий: суббота/воскресенье для отдельного окна торгов."""
        current = now or datetime.now(ZoneInfo("Europe/Moscow"))
        return current.weekday() in (5, 6)

    def _weekend_session(self, now: datetime, *, market_data_live: bool):
        # Субботнее и воскресное окна работают только на подтверждённом live-потоке.
        # Это не разрешает торговлю по календарю вслепую: при отсутствии свежих
        # биржевых данных allow_entries остаётся False.
        if now.weekday() not in (5, 6):
            return {"phase": "closed", "allow_entries": False, "reason": "weekend_closed"}
        if now.date() in self.WEEKEND_CLOSED_DATES_2026:
            return {"phase": "closed", "allow_entries": False, "reason": "exchange_calendar_closed"}

        now_min = self._minute_of_day(now.hour, now.minute)
        weekend_start = 10 * 60
        weekend_end = 19 * 60

        if weekend_start <= now_min < weekend_end:
            if market_data_live:
                return {"phase": "weekend_live", "allow_entries": True, "reason": "verified_live_stream"}
            return {"phase": "weekend_waiting_stream", "allow_entries": False, "reason": "live_stream_required"}

        return {"phase": "closed", "allow_entries": False, "reason": "outside_weekend_window"}

    def next_entry_session(self, *, symbol: str | None = None, now: datetime | None = None) -> datetime:
        current = now or datetime.now(ZoneInfo("Europe/Moscow"))
        for offset in range(0, 10):
            day = current.date() + timedelta(days=offset)
            start_hour, start_minute = ((6, 50) if symbol and "@MISX" in symbol.upper() else (8, 50))
            candidate = datetime(day.year, day.month, day.day, start_hour, start_minute, tzinfo=current.tzinfo)
            probe = candidate.replace(hour=10, minute=0)
            if candidate <= current:
                continue
            if self.get_regime(symbol, now=probe, market_data_live=True).get("allow_entries"):
                return candidate
        return current + timedelta(days=10)

    def _forts_session(self, h, m):
        now_min = self._minute_of_day(h, m)

        # Русский комментарий: срочный рынок MOEX.
        # Утренняя торговая сессия: 08:50–10:00 МСК.
        # Основная торговая сессия: 10:00–19:00 МСК.
        # Вечерняя торговая сессия: 19:00–23:50 МСК.
        morning_start = 8 * 60 + 50
        main_start = 10 * 60
        evening_start = 19 * 60
        trading_end = 23 * 60 + 50

        if now_min < morning_start:
            return {"phase": "preopen", "allow_entries": False}
        if morning_start <= now_min < main_start:
            return {"phase": "morning", "allow_entries": True}
        if main_start <= now_min < evening_start:
            return {"phase": "main", "allow_entries": True}
        if evening_start <= now_min < trading_end:
            return {"phase": "evening", "allow_entries": True}

        return {"phase": "closed", "allow_entries": False}

    def _stock_session(self, h, m):
        now_min = self._minute_of_day(h, m)

        # Русский комментарий: фондовый рынок MOEX.
        # Утренняя дополнительная сессия: 06:50–09:50 МСК.
        # Основная сессия: 09:50–19:00 МСК.
        # Вечерняя дополнительная сессия: 19:00–23:50 МСК.
        morning_start = 6 * 60 + 50
        main_start = 9 * 60 + 50
        evening_start = 19 * 60
        trading_end = 23 * 60 + 50

        if now_min < morning_start:
            return {"phase": "closed", "allow_entries": False}
        if morning_start <= now_min < main_start:
            return {"phase": "morning", "allow_entries": True}
        if main_start <= now_min < evening_start:
            return {"phase": "main", "allow_entries": True}
        if evening_start <= now_min < trading_end:
            return {"phase": "evening", "allow_entries": True}

        return {"phase": "closed", "allow_entries": False}
    WEEKEND_CLOSED_DATES_2026 = {
        date(2026,1,3),date(2026,1,4),date(2026,1,10),date(2026,1,11),
        date(2026,2,14),date(2026,2,15),date(2026,3,7),date(2026,3,8),
        date(2026,3,21),date(2026,3,22),date(2026,5,9),date(2026,5,10),
        date(2026,6,20),date(2026,6,21),date(2026,8,1),date(2026,8,2),
        date(2026,8,15),date(2026,8,16),date(2026,9,12),date(2026,9,13),
        date(2026,10,24),date(2026,10,25),date(2026,12,5),date(2026,12,6),
    }

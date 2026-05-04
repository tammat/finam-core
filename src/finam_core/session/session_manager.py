# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime


class SessionManager:
    """Русский комментарий: определяет торговую фазу MOEX для PAPER/live-paper gate."""

    def __init__(self, market: str = "FORTS") -> None:
        self.market = str(market or "FORTS").upper()

    def get_regime(self, symbol: str | None = None):
        now = datetime.now()
        h = now.hour
        m = now.minute

        # Русский комментарий: на выходных отдельное окно торгов 10:00–19:00 МСК.
        if self._is_weekend():
            return self._weekend_session(h, m)

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

    def _is_weekend(self) -> bool:
        """Русский комментарий: суббота/воскресенье для отдельного окна торгов."""
        return datetime.now().weekday() in (5, 6)

    def _weekend_session(self, h, m):
        now_min = self._minute_of_day(h, m)
        weekend_start = 10 * 60
        weekend_end = 19 * 60

        if weekend_start <= now_min < weekend_end:
            return {"phase": "weekend", "allow_entries": True}

        return {"phase": "closed", "allow_entries": False}

    def _forts_session(self, h, m):
        now_min = self._minute_of_day(h, m)

        # Русский комментарий: срочный рынок MOEX.
        # Утренняя торговая сессия: 09:00–10:00 МСК.
        # Основная торговая сессия: 10:00–19:00 МСК.
        # Вечерняя торговая сессия: 19:00–23:50 МСК.
        morning_start = 9 * 60
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

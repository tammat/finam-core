# Patched SessionManager (FORTS-aware)

from datetime import datetime


class SessionManager:
    def get_regime(self, symbol: str | None = None):
        now = datetime.now()
        h = now.hour
        m = now.minute
        wd = now.weekday()

        # === WEEKEND BLOCK ===
        if wd >= 5:
            return {"phase": "weekend", "allow_entries": False}

        # === FORTS DETECT ===
        if symbol and "@" in symbol:
            return self._forts_session(h, m)

        # fallback (stocks)
        return self._stock_session(h, m)

    # =========================================================
    # === FORTS SESSION ===
    # =========================================================
    def _minute_of_day(self, h: int, m: int) -> int:
        return int(h) * 60 + int(m)

    def _forts_session(self, h, m):
        now_min = self._minute_of_day(h, m)

        # Русский комментарий: актуальное расписание Срочного рынка MOEX после перехода на ЕТС.
        # Утренняя торговая сессия: 09:00–10:00 МСК.
        # Основная торговая сессия: 10:00–19:00 МСК.
        # Вечерняя торговая сессия: 19:00–23:50 МСК.
        # Аукцион открытия 08:50–09:00 не используем для новых входов.
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

        # Русский комментарий: фондовый рынок MOEX: утренняя, основная и вечерняя сессии.
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


# src/finam_core/session/session_manager.py
# Русский коммент: управление торговыми сессиями MOEX (упрощённая версия)

from datetime import datetime, time, timedelta
import os


class SessionManager:
    def __init__(self):
        self.mode = os.getenv("MODE", "live")  # live / sim / debug

        # UTC время (MOEX ~ UTC+3)
        # Можно позже вынести в config
        self.start_hour = int(os.getenv("SESSION_START_HOUR", "7"))
        self.end_hour = int(os.getenv("SESSION_END_HOUR", "20"))

        self.warmup_minutes = int(os.getenv("SESSION_WARMUP_MIN", "10"))

    def is_market_open(self, now=None):
        if self.mode in ("sim", "debug"):
            return True

        now = now or datetime.utcnow()
        hour = now.hour

        return self.start_hour <= hour <= self.end_hour

    def is_warmup(self, now=None):
        now = now or datetime.utcnow()

        session_start = now.replace(
            hour=self.start_hour, minute=0, second=0, microsecond=0
        )

        return session_start <= now <= session_start + timedelta(minutes=self.warmup_minutes)

    def allow_trading(self, now=None):
        if self.mode == "debug":
            return True

        if not self.is_market_open(now):
            return False

        if self.is_warmup(now):
            return False

        return True

    def get_state(self, now=None):
        now = now or datetime.utcnow()

        return {
            "mode": self.mode,
            "market_open": self.is_market_open(now),
            "warmup": self.is_warmup(now),
            "trading_allowed": self.allow_trading(now),
        }

    def get_regime(self):
        return {
            "phase": "pre/open/core/close",
            "allow_entries": True / False,
            "allow_exits": True / False,
        }
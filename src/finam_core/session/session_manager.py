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
        # DEBUG/SIM всегда открыто
        if self.mode in ("sim", "debug"):
            return True

        now = now or datetime.utcnow()

        # корректный перевод UTC → MSK
        now_msk = now + timedelta(hours=3)

        # проверка дня недели (MOEX не торгует в выходные)
        if now_msk.weekday() >= 5:
            return False

        # диапазон сессии
        session_start = time(self.start_hour, 0)
        session_end = time(self.end_hour, 0)

        return session_start <= now_msk.time() <= session_end

    def is_warmup(self, now=None):
        now = now or datetime.utcnow()

        # MSK время
        now_msk = now + timedelta(hours=3)

        session_start = now_msk.replace(
            hour=self.start_hour, minute=0, second=0, microsecond=0
        )

        return session_start <= now_msk <= session_start + timedelta(minutes=self.warmup_minutes)

    def allow_trading(self, now=None):
        regime = self.get_regime(now)
        return regime.get("allow_entries", False)

    def get_state(self, now=None):
        now = now or datetime.utcnow()

        # ЕДИНЫЙ источник истины
        regime = self.get_regime(now)

        return {
            "mode": self.mode,
            "market_open": regime.get("market_open", True),
            "warmup": regime.get("phase") == "warmup",
            "trading_allowed": regime.get("allow_entries", False),
        }

    def get_regime(self, now=None):
        now = now or datetime.utcnow()

        # override (форс-режим) — ВАЖНО: раньше проверки market_open
        override = os.getenv("SESSION_OVERRIDE", "0") == "1"

        if override:
            print("PIPE_SESSION_OVERRIDE_ACTIVE", flush=True)
            return {
                "phase": "override",
                "allow_entries": True,
                "allow_exits": True,
                "market_open": True,
                "reason": "manual_override",
            }

        # режимы для debug/sim — всегда торгуем
        if self.mode in ("debug", "sim"):
            return {
                "phase": "core",
                "allow_entries": True,
                "allow_exits": True,
                "market_open": True,
                "reason": "sim_or_debug",
            }

        market_open = self.is_market_open(now)
        warmup = self.is_warmup(now)

        # SAFETY: если нет рынка — блок
        if not market_open:
            print("PIPE_SESSION_CLOSED", flush=True)
            return {
                "phase": "closed",
                "allow_entries": False,
                "allow_exits": False,
                "market_open": False,
                "reason": "market_closed",
            }

        # фаза
        if warmup:
            phase = "warmup"
        else:
            phase = "core"

        # логика допуска
        allow_entries = not warmup
        allow_exits = True

        print(f"PIPE_SESSION phase={phase} allow_entries={allow_entries}", flush=True)

        return {
            "phase": phase,
            "allow_entries": allow_entries,
            "allow_exits": allow_exits,
            "market_open": True,
            "reason": "warmup_block" if warmup else "normal",
        }
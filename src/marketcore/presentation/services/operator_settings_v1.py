from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True, slots=True)
class OperatorSettingsV1:
    timezone: str
    currency: str
    broker: str

    TIMEZONES = ("Europe/Moscow", "UTC", "Europe/Helsinki")
    CURRENCIES = ("RUB", "USD", "EUR")
    BROKERS = ("Finam", "T-Bank", "QUIK", "Interactive Brokers")

    @classmethod
    def load(cls, *, timezone: str | None = None, currency: str | None = None, broker: str | None = None) -> "OperatorSettingsV1":
        return cls(
            timezone=cls._value(timezone, "MARKETCORE_TIMEZONE", "Europe/Moscow", cls.TIMEZONES),
            currency=cls._value(currency, "MARKETCORE_CURRENCY", "RUB", cls.CURRENCIES),
            broker=cls._value(broker, "MARKETCORE_BROKER", "Finam", cls.BROKERS),
        )

    @classmethod
    def _value(cls, override: str | None, name: str, default: str, allowed: tuple[str, ...]) -> str:
        if override is not None:
            value = str(override).strip()
            return value if value in allowed else default
        return cls._choice(name, default, allowed)

    @staticmethod
    def _choice(name: str, default: str, allowed: tuple[str, ...]) -> str:
        value = os.getenv(name, default).strip()
        return value if value in allowed else default

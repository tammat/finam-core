from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LocaleSettings:
    locale: str = "ru"
    timezone: str = "Europe/Moscow"
    currency: str = "RUB"
    theme: str = "dark"


class LocaleService:
    def __init__(self, settings: LocaleSettings | None = None) -> None:
        self.settings = settings or LocaleSettings()

    @property
    def locale(self) -> str:
        return self.settings.locale

    @property
    def timezone(self) -> str:
        return self.settings.timezone

    @property
    def currency(self) -> str:
        return self.settings.currency

    @property
    def theme(self) -> str:
        return self.settings.theme

from __future__ import annotations

from marketcore.presentation.services.currency_service import CurrencyService
from marketcore.presentation.services.datetime_service import DateTimeService
from marketcore.presentation.services.i18n_service import I18NService
from marketcore.presentation.services.locale_service import LocaleService
from marketcore.presentation.services.number_service import NumberService
from marketcore.presentation.services.unit_service import UnitService


class FormatterService:
    def __init__(
        self,
        locale: LocaleService,
        numbers: NumberService,
        currency: CurrencyService,
        datetime_service: DateTimeService,
        units: UnitService,
        i18n: I18NService,
    ) -> None:
        self.locale = locale
        self.numbers = numbers
        self.currency = currency
        self.datetime_service = datetime_service
        self.units = units
        self.i18n = i18n

    def number(self, value, precision: int = 2) -> str:
        return self.numbers.format_number(value, precision)

    def percent(self, value, precision: int = 2) -> str:
        return self.numbers.format_percent(value, precision)

    def ratio(self, value, precision: int = 4) -> str:
        return self.numbers.format_ratio(value, precision)

    def money(self, value, currency: str | None = None, precision: int = 2) -> str:
        return self.currency.format_money(
            value=value,
            currency=currency or self.locale.currency,
            precision=precision,
        )

    def datetime(self, value) -> str:
        return self.datetime_service.format_datetime(
            value=value,
            timezone=self.locale.timezone,
        )

    def unit(self, key: str) -> str:
        return self.units.label(key)

    def label(self, object_type: str, object_key: str) -> str:
        return self.i18n.label(
            object_type=object_type,
            object_key=object_key,
            locale=self.locale.locale,
        )

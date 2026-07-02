from __future__ import annotations

from dataclasses import dataclass

from marketcore.presentation.api_client import get_json
from marketcore.presentation.services.currency_service import CurrencyService
from marketcore.presentation.services.datetime_service import DateTimeService
from marketcore.presentation.services.formatter_service import FormatterService
from marketcore.presentation.services.i18n_service import I18NService
from marketcore.presentation.services.icon_service import IconService
from marketcore.presentation.services.locale_service import LocaleService
from marketcore.presentation.services.number_service import NumberService
from marketcore.presentation.services.status_service import StatusService
from marketcore.presentation.services.unit_service import UnitService


@dataclass(frozen=True)
class PresentationContext:
    locale: LocaleService
    numbers: NumberService
    currency: CurrencyService
    datetime: DateTimeService
    units: UnitService
    i18n: I18NService
    icons: IconService
    status: StatusService
    formatter: FormatterService

    def api_get(self, path: str, timeout: float = 2.0) -> dict:
        return get_json(path, timeout=timeout)


def build_presentation_context() -> PresentationContext:
    locale = LocaleService()
    numbers = NumberService()
    currency = CurrencyService(numbers)
    datetime_service = DateTimeService()
    units = UnitService()
    i18n = I18NService()
    icons = IconService()
    status = StatusService()

    formatter = FormatterService(
        locale=locale,
        numbers=numbers,
        currency=currency,
        datetime_service=datetime_service,
        units=units,
        i18n=i18n,
    )

    return PresentationContext(
        locale=locale,
        numbers=numbers,
        currency=currency,
        datetime=datetime_service,
        units=units,
        i18n=i18n,
        icons=icons,
        status=status,
        formatter=formatter,
    )

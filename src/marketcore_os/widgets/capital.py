from __future__ import annotations

from decimal import Decimal

from marketcore_os.services.capital import CapitalService
from marketcore_os.widgets.base import SimpleWidget, row, tr


def money(value: Decimal, currency: str) -> str:
    rounded = value.quantize(Decimal("0.01"))
    text = f"{rounded:,.2f}".replace(",", " ")
    symbol = "₽" if currency == "RUB" else currency
    return f"{text} {symbol}"


def pct(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}%"


class CapitalWidget(SimpleWidget):
    def __init__(self, service: CapitalService | None = None) -> None:
        super().__init__(
            widget_id="W003_CAPITAL",
            title_ru="Капитал",
            title_en="Capital",
            priority=20,
            refresh_interval_sec=30,
            workspace="workspace",
        )
        self.service = service or CapitalService()

    def body(self, lang: str) -> str:
        vm = self.service.get_widget_model(display_currency="RUB")
        return (
            row(tr(lang, "Плановый капитал", "Planned capital"), money(vm.planned_capital, vm.display_currency))
            + row(tr(lang, "Работает", "Working"), pct(vm.working_pct))
            + row(tr(lang, "Свободно", "Available"), pct(vm.available_pct))
            + row(tr(lang, "Сегодня", "Today"), money(vm.today_pnl, vm.display_currency))
            + row(tr(lang, "Источник", "Source"), vm.data_source)
        )


capital_widget = CapitalWidget()

from __future__ import annotations

from decimal import Decimal

from marketcore_os.repositories.capital import CapitalRepository
from marketcore_os.viewmodels.capital import CapitalViewModel


class CapitalService:
    def __init__(self, repository: CapitalRepository | None = None) -> None:
        self.repository = repository or CapitalRepository()

    def get_widget_model(self, display_currency: str = "RUB") -> CapitalViewModel:
        data = self.repository.load()

        planned = Decimal(str(data["planned_capital"]))
        working = Decimal(str(data["working_capital"]))
        available = Decimal(str(data["available_capital"]))

        working_pct = Decimal("0") if planned == 0 else (working / planned * Decimal("100"))
        available_pct = Decimal("0") if planned == 0 else (available / planned * Decimal("100"))

        return CapitalViewModel(
            planned_capital=planned,
            working_capital=working,
            available_capital=available,
            working_pct=working_pct,
            available_pct=available_pct,
            today_pnl=Decimal(str(data["today_pnl"])),
            base_currency=str(data["base_currency"]),
            display_currency=display_currency,
            fx_source="CBR",
            data_source=str(data["data_source"]),
        )

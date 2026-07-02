from __future__ import annotations

from marketcore_os.services.risk import RiskService
from marketcore_os.widgets.base import SimpleWidget, badge, row, tr


def on_off(value: bool) -> str:
    return badge("ON", "bad") if value else badge("OFF", "off")


class RiskWidget(SimpleWidget):
    def __init__(self, service: RiskService | None = None) -> None:
        super().__init__(
            widget_id="W006_RISK",
            title_ru="Риск",
            title_en="Risk",
            priority=50,
            refresh_interval_sec=30,
            workspace="workspace",
        )
        self.service = service or RiskService()

    def body(self, lang: str) -> str:
        vm = self.service.get_widget_model()
        return (
            row("Runtime", on_off(vm.runtime_allowed))
            + row("Execution", on_off(vm.execution_allowed))
            + row("Micro Live", on_off(vm.micro_live_allowed))
            + row("Daily Risk", f"{vm.daily_risk_pct.quantize(__import__('decimal').Decimal('0.00'))}%")
            + row(tr(lang, "Статус", "Status"), badge(vm.risk_status, "ok" if vm.risk_status == "SAFE" else "bad"))
            + row(tr(lang, "Источник", "Source"), vm.data_source)
        )


risk_widget = RiskWidget()

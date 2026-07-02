from __future__ import annotations

from marketcore_os.services.program import ProgramService
from marketcore_os.widgets.base import SimpleWidget, badge, row, tr


def status_badge(status: str) -> str:
    kind = "ok" if status == "COMPLETE" else "info"
    if status in {"WAITING", "OFF", "BLOCKED"}:
        kind = "off"
    return badge(status, kind)


class ProgramWidget(SimpleWidget):
    def __init__(self, service: ProgramService | None = None) -> None:
        super().__init__(
            widget_id="W002_PROGRAM",
            title_ru="Статус программы",
            title_en="Program Status",
            priority=90,
            refresh_interval_sec=60,
            workspace="workspace",
        )
        self.service = service or ProgramService()

    def body(self, lang: str) -> str:
        vm = self.service.get_widget_model()
        return (
            row(vm.quarter, badge("ACTIVE", "info"))
            + row(tr(lang, "Платформа", "Platform"), status_badge(vm.platform_status))
            + row(tr(lang, "Исследования", "Research"), status_badge(vm.research_status))
            + row("TOP3", status_badge(vm.top3_status))
            + row("Paper", status_badge(vm.paper_status))
            + row("MarketCore OS", status_badge(vm.marketcore_status))
            + row(tr(lang, "Источник", "Source"), vm.data_source)
        )


program_widget = ProgramWidget()

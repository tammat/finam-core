from __future__ import annotations

from marketcore_os.services.profit import ProfitService
from marketcore_os.widgets.base import SimpleWidget, badge, row, tr


class ProfitWidget(SimpleWidget):
    def __init__(self, service: ProfitService | None = None) -> None:
        super().__init__(
            widget_id="W004_PROFIT",
            title_ru="Двигатель прибыли",
            title_en="Profit Engine",
            priority=30,
            refresh_interval_sec=30,
            workspace="workspace",
        )
        self.service = service or ProfitService()

    def body(self, lang: str) -> str:
        vm = self.service.get_widget_model()
        return (
            row("Production", str(vm.production_edges))
            + row("Paper", str(vm.paper_edges))
            + row("Paper Status", badge(vm.paper_status, "info" if vm.paper_status == "READY" else "off"))
            + row("Shadow", str(vm.shadow_edges))
            + row("Research Candidate", str(vm.research_candidates))
            + row(tr(lang, "Источник", "Source"), vm.data_source)
        )


profit_widget = ProfitWidget()

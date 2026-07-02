from __future__ import annotations

from marketcore_os.services.research import ResearchService
from marketcore_os.widgets.base import SimpleWidget, badge, row, tr


class ResearchWidget(SimpleWidget):
    def __init__(self, service: ResearchService | None = None) -> None:
        super().__init__(
            widget_id="W005_RESEARCH",
            title_ru="Исследования",
            title_en="Research",
            priority=40,
            refresh_interval_sec=60,
            workspace="workspace",
        )
        self.service = service or ResearchService()

    def body(self, lang: str) -> str:
        vm = self.service.get_widget_model()
        return (
            row("Pipeline", badge(vm.pipeline_status, "ok"))
            + row("TOP3 Validation", badge(vm.top3_status, "ok" if vm.top3_status == "COMPLETE" else "info"))
            + row("Edge Factory", badge(vm.edge_factory_status, "info" if vm.edge_factory_status == "READY" else "off"))
            + row("Research Candidate", str(vm.research_candidates))
            + row("OOS PASS", str(vm.oos_pass))
            + row("Paper Ready", str(vm.paper_ready))
            + row(tr(lang, "Источник", "Source"), vm.data_source)
        )


research_widget = ResearchWidget()

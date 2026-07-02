from __future__ import annotations

from marketcore_os.repositories.profit import ProfitRepository
from marketcore_os.viewmodels.profit import ProfitViewModel


class ProfitService:
    def __init__(self, repository: ProfitRepository | None = None) -> None:
        self.repository = repository or ProfitRepository()

    def get_widget_model(self) -> ProfitViewModel:
        data = self.repository.load()

        paper_edges = int(data["paper_edges"])
        shadow_edges = int(data["shadow_edges"])

        return ProfitViewModel(
            production_edges=int(data["production_edges"]),
            paper_edges=paper_edges,
            shadow_edges=shadow_edges,
            research_candidates=int(data["research_candidates"]),
            paper_status="READY" if paper_edges > 0 else "WAITING",
            shadow_status="ACTIVE" if shadow_edges > 0 else "WAITING",
            data_source=str(data["data_source"]),
        )

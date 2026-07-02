from __future__ import annotations

from marketcore_os.repositories.research import ResearchRepository
from marketcore_os.viewmodels.research import ResearchViewModel


class ResearchService:
    def __init__(self, repository: ResearchRepository | None = None) -> None:
        self.repository = repository or ResearchRepository()

    def get_widget_model(self) -> ResearchViewModel:
        data = self.repository.load()

        candidates = int(data["research_candidates"])
        oos_pass = int(data["oos_pass"])
        paper_ready = int(data["paper_ready"])

        return ResearchViewModel(
            pipeline_status="COMPLETE" if candidates >= 0 else "UNKNOWN",
            top3_status="COMPLETE" if paper_ready >= 3 else "IN PROGRESS",
            edge_factory_status="READY" if candidates > 0 else "WAITING",
            research_candidates=candidates,
            oos_pass=oos_pass,
            paper_ready=paper_ready,
            data_source=str(data["data_source"]),
        )

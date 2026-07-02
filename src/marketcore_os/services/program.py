from __future__ import annotations

from marketcore_os.repositories.program import ProgramRepository
from marketcore_os.viewmodels.program import ProgramViewModel


class ProgramService:
    def __init__(self, repository: ProgramRepository | None = None) -> None:
        self.repository = repository or ProgramRepository()

    def get_widget_model(self) -> ProgramViewModel:
        data = self.repository.load()
        return ProgramViewModel(
            quarter=str(data["quarter"]),
            platform_status=str(data["platform_status"]),
            research_status=str(data["research_status"]),
            top3_status=str(data["top3_status"]),
            paper_status=str(data["paper_status"]),
            marketcore_status=str(data["marketcore_status"]),
            data_source=str(data["data_source"]),
        )

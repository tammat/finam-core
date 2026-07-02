from __future__ import annotations

from decimal import Decimal

from marketcore_os.repositories.risk import RiskRepository
from marketcore_os.viewmodels.risk import RiskViewModel


class RiskService:
    def __init__(self, repository: RiskRepository | None = None) -> None:
        self.repository = repository or RiskRepository()

    def get_widget_model(self) -> RiskViewModel:
        data = self.repository.load()

        runtime_allowed = bool(data["runtime_allowed"])
        execution_allowed = bool(data["execution_allowed"])
        micro_live_allowed = bool(data["micro_live_allowed"])

        risk_status = "BLOCKED" if (
            runtime_allowed or execution_allowed or micro_live_allowed
        ) else "SAFE"

        return RiskViewModel(
            runtime_allowed=runtime_allowed,
            execution_allowed=execution_allowed,
            micro_live_allowed=micro_live_allowed,
            daily_risk_pct=Decimal(str(data["daily_risk_pct"])),
            risk_status=risk_status,
            data_source=str(data["data_source"]),
        )

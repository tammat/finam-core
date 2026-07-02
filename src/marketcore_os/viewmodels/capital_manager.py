from dataclasses import dataclass


@dataclass(frozen=True)
class CapitalManagerViewModel:
    planned_capital: float
    working_capital: float
    available_capital: float
    exposure_pct: float
    deployment_limit_pct: float
    risk_mode: str
    manager_status: str
    next_action: str
    data_source: str

from dataclasses import dataclass


@dataclass(frozen=True)
class DailyCenterViewModel:
    day_status: str
    capital_status: str
    research_status: str
    risk_status: str
    runtime_status: str
    next_action: str
    decision_hint: str
    data_source: str

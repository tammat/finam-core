from dataclasses import dataclass

@dataclass(frozen=True)
class IntradayViewModel:
    runtime_status: str
    paper_status: str
    production_status: str
    active_symbols: int
    active_edges: int
    active_positions: int
    exposure_pct: float
    next_action: str
    data_source: str

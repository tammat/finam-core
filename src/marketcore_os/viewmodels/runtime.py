from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeCenterViewModel:
    runtime_status: str
    paper_status: str
    production_status: str
    risk_status: str
    active_symbols: int
    active_edges: int
    active_positions: int
    signals_today: int
    trades_today: int
    pnl_today: float
    next_action: str
    data_source: str

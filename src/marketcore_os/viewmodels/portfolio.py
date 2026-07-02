from dataclasses import dataclass

@dataclass(frozen=True)
class PortfolioViewModel:
    planned_capital: float
    working_capital: float
    available_capital: float
    today_pnl: float
    open_positions: int
    paper_positions: int
    production_positions: int
    exposure_pct: float
    portfolio_status: str
    next_action: str
    data_source: str

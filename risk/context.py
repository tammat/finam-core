from dataclasses import dataclass
from typing import Dict
from accounting.position_manager import Position


@dataclass
class RiskContext:
    cash: float
    equity: float
    gross_exposure: float
    drawdown: float
    positions: Dict[str, Position]
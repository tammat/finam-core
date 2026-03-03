# domain/risk/risk_policy.py

from dataclasses import dataclass, field
from typing import Dict, Optional
import hashlib
import json


@dataclass(frozen=True)
class RiskPolicy:

    version: str

    # Exposure
    max_total_exposure: float = 0.6
    max_symbol_exposure: float = 0.2

    # Post-trade
    max_drawdown: float = 0.2
    max_daily_loss: float = 0.05

    # Portfolio heat
    max_portfolio_heat: Optional[float] = None

    # Correlation
    correlation_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    max_correlation: Optional[float] = None

    def fingerprint(self) -> str:
        payload = json.dumps(self.__dict__, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()
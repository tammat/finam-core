from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RiskViewModel:
    runtime_allowed: bool
    execution_allowed: bool
    micro_live_allowed: bool
    daily_risk_pct: Decimal
    risk_status: str
    data_source: str

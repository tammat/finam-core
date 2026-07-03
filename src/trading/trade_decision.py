from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from risk.foundation.risk_verdict import RiskVerdict


@dataclass(frozen=True)
class TradeDecision:
    action: str
    symbol: str
    side: str
    approved_quantity: Decimal
    risk_verdict: RiskVerdict
    decision_reason: str

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reason: Optional[str] = None
    adjusted_quantity: Optional[float] = None
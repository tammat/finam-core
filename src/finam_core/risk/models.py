# risk/models.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class RiskDecision:
    allowed: bool
    rule_name: Optional[str] = None
    reason: Optional[str] = None
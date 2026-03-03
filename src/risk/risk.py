from dataclasses import dataclass


@dataclass
class RiskDecision:
    allowed: bool
    rule_name: str | None = None
    reason: str | None = None
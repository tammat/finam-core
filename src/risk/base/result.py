from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class RiskRuleDiagnostics:
    input_values: dict[str, float]
    thresholds: dict[str, float]
    component_scores: dict[str, float]
    execution_time_ms: float
    details: dict[str, Any]


@dataclass(slots=True, frozen=True)
class RiskRuleResult:
    rule_name: str
    rule_version: str
    risk_score: float
    passed: bool
    diagnostics: RiskRuleDiagnostics
    reason_code: str

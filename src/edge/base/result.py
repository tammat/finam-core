from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class EdgeRuleDiagnostics:
    input_values: dict[str, float]
    weights: dict[str, float]
    component_scores: dict[str, float]
    execution_time_ms: float
    details: dict[str, Any]


@dataclass(slots=True, frozen=True)
class EdgeRuleResult:
    rule_name: str
    rule_version: str
    score: float
    diagnostics: EdgeRuleDiagnostics
    reason_code: str

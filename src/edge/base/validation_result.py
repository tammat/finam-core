from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(slots=True, frozen=True)
class EdgeValidationDiagnostics:
    passed_rules: list[str]
    failed_rules: list[str]
    input_values: dict[str, float]
    thresholds: dict[str, float]
    component_scores: dict[str, float]
    execution_time_ms: float
    details: dict[str, Any]

@dataclass(slots=True, frozen=True)
class EdgeValidationResult:
    rule_name: str
    rule_version: str
    validation_score: float
    passed: bool
    diagnostics: EdgeValidationDiagnostics
    reason_code: str

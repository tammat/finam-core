from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class StrategyDiagnostics:
    passed_filters: list[str]
    failed_filters: list[str]
    feature_values: dict[str, float]
    thresholds: dict[str, float]
    score_breakdown: dict[str, float]
    execution_time_ms: float
    details: dict[str, Any]

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from marketcore.normalization.metrics import NormalizationMetrics


@dataclass
class NormalizationResult:
    success: bool
    metrics: NormalizationMetrics
    errors: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class EdgeScoreRuleConfig:
    signal_score_weight: float = 0.40
    confidence_weight: float = 0.40
    feature_quality_weight: float = 0.20

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EdgeScoreRuleConfig":
        data = data or {}
        return cls(
            signal_score_weight=float(data.get("signal_score_weight", cls.signal_score_weight)),
            confidence_weight=float(data.get("confidence_weight", cls.confidence_weight)),
            feature_quality_weight=float(data.get("feature_quality_weight", cls.feature_quality_weight)),
        )

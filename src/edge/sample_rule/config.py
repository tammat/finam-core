from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(slots=True, frozen=True)
class EdgeSampleRuleConfig:
    min_samples: int = 30
    min_edge_score: float = 0.60

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EdgeSampleRuleConfig":
        data = data or {}
        defaults = cls()
        return cls(
            min_samples=int(data.get("min_samples", defaults.min_samples)),
            min_edge_score=float(data.get("min_edge_score", defaults.min_edge_score)),
        )

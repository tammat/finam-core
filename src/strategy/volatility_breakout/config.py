from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class VolatilityBreakoutConfig:
    min_range_pct: float = 0.8
    min_body_pct: float = 0.5
    min_volume_ratio20: float = 1.2
    min_feature_quality: float = 0.85
    min_return1_pct: float = 0.0
    min_return5_pct: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "VolatilityBreakoutConfig":
        data = data or {}
        return cls(
            min_range_pct=float(data.get("min_range_pct", cls.min_range_pct)),
            min_body_pct=float(data.get("min_body_pct", cls.min_body_pct)),
            min_volume_ratio20=float(data.get("min_volume_ratio20", cls.min_volume_ratio20)),
            min_feature_quality=float(data.get("min_feature_quality", cls.min_feature_quality)),
            min_return1_pct=float(data.get("min_return1_pct", cls.min_return1_pct)),
            min_return5_pct=float(data.get("min_return5_pct", cls.min_return5_pct)),
        )

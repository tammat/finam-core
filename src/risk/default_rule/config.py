from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class DefaultRiskRuleConfig:
    min_edge_score: float = 0.60
    min_validation_score: float = 0.70
    max_risk_per_trade: float = 0.01
    exposure_limit: float = 0.10
    kill_switch_enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "DefaultRiskRuleConfig":
        data = data or {}
        defaults = cls()
        return cls(
            min_edge_score=float(data.get("min_edge_score", defaults.min_edge_score)),
            min_validation_score=float(data.get("min_validation_score", defaults.min_validation_score)),
            max_risk_per_trade=float(data.get("max_risk_per_trade", defaults.max_risk_per_trade)),
            exposure_limit=float(data.get("exposure_limit", defaults.exposure_limit)),
            kill_switch_enabled=bool(data.get("kill_switch_enabled", defaults.kill_switch_enabled)),
        )

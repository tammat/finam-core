from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ContextQualityResult:
    quality: str
    missing_fields: list[str]


class ContextQualityEngine:
    """Русский комментарий: оценивает полноту контекста сделки для research/promotion."""

    REQUIRED_FIELDS = {
        "strategy": "strategy",
        "timeframe": "timeframe",
        "risk.heat_status": "risk",
        "strategy_context.exit_policy": "strategy_context",
        "feature_snapshot": "feature_snapshot",
    }

    def evaluate(self, payload: dict[str, Any]) -> ContextQualityResult:
        missing: list[str] = []

        for field, root in self.REQUIRED_FIELDS.items():
            if "." not in field:
                if not payload.get(field):
                    missing.append(field)
                continue

            root_key, child_key = field.split(".", 1)
            root_value = payload.get(root_key) or {}
            if not isinstance(root_value, dict) or not root_value.get(child_key):
                missing.append(field)

        if not missing:
            quality = "FULL"
        elif len(missing) <= 2:
            quality = "PARTIAL"
        elif len(missing) < len(self.REQUIRED_FIELDS):
            quality = "WEAK"
        else:
            quality = "BROKEN"

        return ContextQualityResult(quality=quality, missing_fields=missing)

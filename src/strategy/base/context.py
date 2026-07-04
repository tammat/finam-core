from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class StrategyContext:
    feature_snapshot: dict[str, Any]
    configuration: dict[str, Any]
    instrument: dict[str, Any]

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from strategy.base.signal import Signal


@dataclass(slots=True, frozen=True)
class StrategyResult:
    signal: Signal | None
    diagnostics: dict[str, Any]
    execution_time_ms: float
    feature_version: str
    strategy_version: str
    reason: str

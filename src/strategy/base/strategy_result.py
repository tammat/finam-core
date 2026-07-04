from __future__ import annotations

from dataclasses import dataclass

from strategy.base.diagnostics import StrategyDiagnostics
from strategy.base.signal import Signal


@dataclass(slots=True, frozen=True)
class StrategyResult:
    signal: Signal | None
    diagnostics: StrategyDiagnostics
    feature_version: str
    strategy_version: str
    reason: str

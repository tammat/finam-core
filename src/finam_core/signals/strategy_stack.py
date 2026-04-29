# src/finam_core/signals/strategy_stack.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class StrategyStackResult:
    selected: dict[str, Any] | None
    candidates_count: int
    selected_source: str | None
    reason: str


class StrategyStack:
    """
    Русский коммент: минимальный StrategyStack.
    Запрашивает сигналы у нескольких стратегий и выбирает первый валидный по порядку приоритета.
    """

    def __init__(self, strategies: list[Any]):
        self.strategies = list(strategies)

    def on_quote(self, st: dict) -> dict[str, Any] | None:
        result = self.collect(st)
        return result.selected

    def collect(self, st: dict) -> StrategyStackResult:
        candidates: list[dict[str, Any]] = []

        for strategy in self.strategies:
            intent = strategy.on_quote(st)
            if not intent:
                continue

            if isinstance(intent, dict):
                intent = dict(intent)
                intent.setdefault("source", strategy.__class__.__name__)
                candidates.append(intent)

        if not candidates:
            return StrategyStackResult(
                selected=None,
                candidates_count=0,
                selected_source=None,
                reason="no_signal",
            )

        selected = candidates[0]
        return StrategyStackResult(
            selected=selected,
            candidates_count=len(candidates),
            selected_source=selected.get("source"),
            reason="selected_first_by_priority",
        )

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
    Русский коммент: StrategyStack собирает сигналы от нескольких стратегий
    и выбирает лучший по confidence, затем score, затем порядку приоритета.
    """

    def __init__(self, strategies: list[Any]):
        self.strategies = list(strategies)

    def on_quote(self, st: dict) -> dict[str, Any] | None:
        result = self.collect(st)
        return result.selected

    def collect(self, st: dict) -> StrategyStackResult:
        candidates: list[tuple[int, dict[str, Any]]] = []

        for priority, strategy in enumerate(self.strategies):
            intent = strategy.on_quote(st)
            if not intent:
                continue

            if isinstance(intent, dict):
                normalized = dict(intent)
                normalized.setdefault("source", strategy.__class__.__name__)
                normalized.setdefault("confidence", 1.0)
                normalized.setdefault("score", normalized.get("confidence", 1.0))
                normalized["_priority"] = priority
                candidates.append((priority, normalized))

        if not candidates:
            return StrategyStackResult(
                selected=None,
                candidates_count=0,
                selected_source=None,
                reason="no_signal",
            )

        selected = sorted(
            (c for _, c in candidates),
            key=lambda x: (
                float(x.get("confidence", 0.0)),
                float(x.get("score", 0.0)),
                -float(x.get("_priority", 0)),
            ),
            reverse=True,
        )[0]

        selected.pop("_priority", None)

        print(
            f"PIPE_STACK_SELECTED candidates={len(candidates)} "
            f"source={selected.get('source')} "
            f"side={selected.get('side')} "
            f"confidence={selected.get('confidence')} "
            f"score={selected.get('score')} "
            f"reason=selected_by_score",
            flush=True,
        )
        print("DEBUG STACK OUTPUT:", selected, flush=True)
        return StrategyStackResult(
            selected=selected,
            candidates_count=len(candidates),
            selected_source=selected.get("source"),
            reason="selected_by_score",
        )

    def generate(self, st, policy: str = "first"):
        """
        Унифицированный интерфейс для pipeline
        """

        candidates: list[dict[str, Any]] = []

        for priority, strat in enumerate(self.strategies):
            try:
                if hasattr(strat, "on_quote"):
                    signal = strat.on_quote(st)
                elif hasattr(strat, "generate"):
                    signal = strat.generate(st)
                else:
                    continue

                if not signal:
                    continue

                # === НОРМАЛИЗАЦИЯ (ЕДИНАЯ ТОЧКА ИСТИНЫ) ===
                normalized = dict(signal)

                normalized.setdefault("source", strat.__class__.__name__)
                normalized.setdefault("confidence", 1.0)
                normalized.setdefault("score", normalized.get("confidence", 1.0))

                # приоритет стратегии (чем раньше — тем выше)
                normalized["_priority"] = priority

                candidates.append(normalized)

            except Exception as e:
                print(f"[StrategyStack] {strat.__class__.__name__} failed: {e}", flush=True)

        if not candidates:
            return None

        # === СОРТИРОВКА (как в collect) ===
        candidates = sorted(
            candidates,
            key=lambda x: (
                float(x.get("confidence", 0.0)),
                float(x.get("score", 0.0)),
                -float(x.get("_priority", 0)),
            ),
            reverse=True,
        )

        best = candidates[0]
        best.pop("_priority", None)

        print(
            f"PIPE_STACK_SELECTED candidates={len(candidates)} "
            f"source={best.get('source')} "
            f"side={best.get('side')} "
            f"confidence={best.get('confidence')} "
            f"score={best.get('score')} "
            f"reason=selected_by_score",
            flush=True,
        )

        return best
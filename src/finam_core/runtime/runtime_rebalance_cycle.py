from __future__ import annotations

from typing import Any


class RuntimeRebalanceCycle:
    """
    Русский комментарий: единый rebalance-cycle для RuntimeExecutionEngine v3.

    Задача слоя:
    - вызвать RuntimeUniverseAllocator;
    - не дать ошибке allocator уронить бесконечный supervisor-loop;
    - вернуть количество активных инструментов после ротации.
    """

    def __init__(
        self,
        allocator: Any,
        *,
        max_symbols: int = 5,
        min_score: float = 0.35,
    ) -> None:
        self.allocator = allocator
        self.max_symbols = max_symbols
        self.min_score = min_score
        self.last_active_count: int | None = None
        self.last_error: str | None = None

    def __call__(self) -> None:
        try:
            active_count = self.allocator.allocate(
                max_symbols=self.max_symbols,
                min_score=self.min_score,
            )
            self.last_active_count = int(active_count)
            self.last_error = None

            print(
                f"RUNTIME_REBALANCE_OK active_count={self.last_active_count}",
                flush=True,
            )

        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"

            print(
                f"RUNTIME_REBALANCE_ERROR error={self.last_error}",
                flush=True,
            )

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class QuoteSignalInput:
    symbol: str
    state: dict[str, Any]


class QuoteSignalProcessor:
    """
    Русский комментарий:
    Оркестратор обработки quote → raw_intent.

    Первый этап:
    тонкая обёртка над StrategyRuntime.
    Поведение стратегии не меняем.
    """

    def __init__(self, strategy_runtime) -> None:
        self.strategy_runtime = strategy_runtime

    def process(self, data: QuoteSignalInput):
        return self.strategy_runtime.on_quote(data.symbol, data.state)

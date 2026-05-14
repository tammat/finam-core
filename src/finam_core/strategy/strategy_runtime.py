from __future__ import annotations

from finam_core.strategy.strategy_factory import StrategyFactory


class StrategyRuntime:
    """
    Русский комментарий:
    Runtime-слой для multi-symbol стратегий.

    PaperTradingPipeline больше не должен напрямую:
    - создавать стратегии через StrategyFactory;
    - хранить strategy_by_symbol;
    - знать детали strategy.on_quote().
    """

    def __init__(self) -> None:
        self.strategy_by_symbol = {}

    def get_strategy(self, symbol: str):
        if symbol not in self.strategy_by_symbol:
            self.strategy_by_symbol[symbol] = StrategyFactory.create(symbol)
        return self.strategy_by_symbol[symbol]

    def on_quote(self, symbol: str, state: dict):
        strategy = self.get_strategy(symbol)
        return strategy.on_quote(state)

from __future__ import annotations


class CurrencyRegimeFutures:
    """Явный адаптер валютного фьючерсного генератора.

    Сигналы создаёт существующий market pipeline. Адаптер фиксирует исполнимую
    идентичность стратегии и не содержит общего fallback.
    """

    def __init__(self, strategy_code: str) -> None:
        self.strategy_code = strategy_code

    def on_quote(self, state: dict):
        return None

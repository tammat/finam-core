from typing import List, Any


class StrategyStack:
    """
    Production-grade strategy container.
    Supports ordered strategy evaluation and signal aggregation.
    """

    def __init__(self) -> None:
        self._strategies: List[Any] = []

    def register(self, strategy: Any) -> None:
        if strategy is not None:
            self._strategies.append(strategy)

    def generate(self, market_data: Any) -> List[Any]:
        """
        Returns a list of raw signals from all strategies.
        """
        signals: List[Any] = []

        for strategy in self._strategies:
            if hasattr(strategy, "generate_signal"):
                signal = strategy.generate_signal(market_data)
                if signal:
                    signals.append(signal)

        return signals
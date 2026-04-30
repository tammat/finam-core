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

    def generate(self, market_data: Any, policy: str = "first"):
        signals = []

        for strategy in self._strategies:
            try:
                if hasattr(strategy, "on_quote"):
                    signal = strategy.on_quote(market_data)
                elif hasattr(strategy, "generate"):
                    signal = strategy.generate(market_data)
                else:
                    continue

                if signal:
                    signals.append(signal)

            except Exception as e:
                print(f"[StrategyStack] {strategy.__class__.__name__} failed: {e}")

        if not signals:
            return None

        # === ВЫБОР ===
        if policy == "all":
            return signals

        # default = first
        return signals[0]
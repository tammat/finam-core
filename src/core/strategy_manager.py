# src/core/strategy_manager.py

from __future__ import annotations

from typing import Any, List


class StrategyManager:
    """
    v1 — минимальный менеджер стратегий:
    - хранит список стратегий
    - собирает сигналы (signal|None) от каждой стратегии
    - не допускает падения движка из-за одной стратегии
    """

    def __init__(self) -> None:
        self._strategies: List[Any] = []

    def register(self, strategy: Any) -> None:
        self._strategies.append(strategy)

    def clear(self) -> None:
        self._strategies.clear()

    def generate_signals(self, *args, **kwargs):
        signals = []

        for strategy in self._strategies:
            try:
                # 🔥 Поддержка старого контракта
                if hasattr(strategy, "generate"):
                    signal = strategy.generate()

                elif hasattr(strategy, "on_market_event"):
                    signal = strategy.on_market_event(*args, **kwargs)

                else:
                    continue

                if signal is not None:
                    signals.append(signal)

            except Exception as e:
                print(f"[StrategyManager] {strategy.__class__.__name__} failed: {e}")

        return signals
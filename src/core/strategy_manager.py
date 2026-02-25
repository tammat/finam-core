# src/core/strategy_manager.py

from __future__ import annotations
from typing import Any, List


class StrategyManager:
    """
    v2 — менеджер стратегий:
    - хранит список стратегий
    - защищает движок от падения стратегий
    - поддерживает агрегированную выдачу сигнала (policy)
    """

    def __init__(self) -> None:
        self._strategies: List[Any] = []

    def register(self, strategy: Any) -> None:
        self._strategies.append(strategy)

    def clear(self) -> None:
        self._strategies.clear()

    # =============================
    # Старый контракт (не ломаем)
    # =============================
    def generate_signals(self, *args, **kwargs):
        """
        Возвращает список всех сигналов.
        Используется для backward compatibility.
        """
        signals = []

        for strategy in self._strategies:
            try:
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

    # =============================
    # Новый контракт (рекомендуемый)
    # =============================
    def generate(self, *args, policy: str = "first", **kwargs):
        """
        policy:
            "first" → вернуть первый валидный сигнал
            "all"   → вернуть список сигналов
            "none"  → всегда None
        """
        signals = self.generate_signals(*args, **kwargs)

        if policy == "none":
            return None

        if policy == "all":
            return signals

        # default = first
        return signals[0] if signals else None
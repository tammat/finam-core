# src/core/strategy_manager.py

from __future__ import annotations
from typing import Any, List, Optional


class StrategyManager:
    """
    v3 — менеджер стратегий (regime-aware):

    - хранит список стратегий
    - не падает при ошибках стратегий
    - поддерживает выбор стратегии по режиму рынка
    - fallback если нет подходящей стратегии
    """

    def __init__(self) -> None:
        self._strategies: List[Any] = []

    def register(self, strategy: Any) -> None:
        self._strategies.append(strategy)

    def clear(self) -> None:
        self._strategies.clear()

    # =============================
    # Старый контракт (оставляем)
    # =============================
    def generate_signals(self, *args, **kwargs):
        signals = []

        for strategy in self._strategies:
            try:
                signal = self._call_strategy(strategy, *args, **kwargs)
                if signal is not None:
                    signals.append(signal)

            except Exception as e:
                print(f"[StrategyManager] {strategy.__class__.__name__} failed: {e}")

        return signals

    # =============================
    # Новый контракт (regime-aware)
    # =============================
    def generate(
        self,
        *args,
        regime: Optional[str] = None,
        policy: str = "first",
        **kwargs
    ):
        """
        regime:
            "trend"
            "range"
            "volatile"
            None → fallback

        policy:
            "first" → первый сигнал
            "all"   → список
            "best"  → лучший по score
        """

        # 1️⃣ фильтруем стратегии по режиму
        filtered = self._filter_by_regime(regime)

        # fallback если ничего не подошло
        if not filtered:
            filtered = self._strategies

        # 2️⃣ собираем сигналы
        signals = []

        for strategy in filtered:
            try:
                signal = self._call_strategy(strategy, *args, **kwargs)
                if signal is not None:
                    signals.append(signal)

            except Exception as e:
                print(f"[StrategyManager] {strategy.__class__.__name__} failed: {e}")

        if not signals:
            return None

        # 3️⃣ политика выбора
        if policy == "all":
            return signals

        if policy == "best":
            return max(signals, key=lambda s: getattr(s, "score", 0))

        # default
        return signals[0]

    # =============================
    # ВНУТРЕННЕЕ
    # =============================
    def _call_strategy(self, strategy: Any, *args, **kwargs):
        if hasattr(strategy, "generate"):
            return strategy.generate(*args, **kwargs)

        if hasattr(strategy, "on_market_event"):
            return strategy.on_market_event(*args, **kwargs)

        return None

    def _filter_by_regime(self, regime: Optional[str]):
        """
        Ожидаем что стратегия имеет:
            strategy.regimes = ["trend", "range"]
        """
        if regime is None:
            return self._strategies

        result = []

        for s in self._strategies:
            regimes = getattr(s, "regimes", None)

            # если стратегия универсальная
            if not regimes:
                result.append(s)
                continue

            if regime in regimes:
                result.append(s)

        return result
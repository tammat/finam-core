from __future__ import annotations

from strategy.base.strategy import Strategy


class StrategyRegistry:
    _registry: dict[str, type[Strategy]] = {}

    @classmethod
    def register(cls, strategy_cls: type[Strategy]) -> type[Strategy]:
        family = getattr(strategy_cls, "family", "")
        if not family:
            raise ValueError("strategy family is required")
        cls._registry[family] = strategy_cls
        return strategy_cls

    @classmethod
    def enabled(cls) -> list[type[Strategy]]:
        return [
            strategy_cls
            for strategy_cls in cls._registry.values()
            if getattr(strategy_cls, "enabled", True)
        ]

    @classmethod
    def get(cls, family: str) -> type[Strategy] | None:
        return cls._registry.get(family)

    @classmethod
    def clear_for_tests(cls) -> None:
        cls._registry.clear()

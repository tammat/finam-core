from __future__ import annotations

import os


class CoordinatorFlags:
    """Русский комментарий: единая точка проверки флагов TradingEngineCoordinator."""

    @staticmethod
    def _enabled(name: str) -> bool:
        return os.getenv(name, "0") == "1"

    @classmethod
    def enabled(cls) -> bool:
        return cls._enabled("ENABLE_ENGINE_COORDINATOR")

    @classmethod
    def on_quote_enabled(cls) -> bool:
        return cls.enabled() or cls._enabled("ENABLE_ENGINE_COORDINATOR_ON_QUOTE")

    @classmethod
    def reconcile_enabled(cls) -> bool:
        return cls.enabled() or cls._enabled("ENABLE_ENGINE_COORDINATOR_RECONCILE")

    @classmethod
    def execution_route_enabled(cls) -> bool:
        return cls.enabled() or cls._enabled("ENABLE_ENGINE_COORDINATOR_EXECUTION_ROUTE")

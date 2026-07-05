from __future__ import annotations

from dataclasses import dataclass

from marketcore.research.execution.interfaces.strategy_engine import StrategyEngine


@dataclass(frozen=True)
class StrategyDispatchResult:
    strategy_code: str
    engine_name: str
    engine_version: str
    engine: StrategyEngine


class StrategyDispatcher:
    def __init__(self, engines: dict[str, StrategyEngine]) -> None:
        self._engines = dict(engines)

    def dispatch(
        self,
        strategy_code: str,
        engine_name: str,
        engine_version: str = "v1",
    ) -> StrategyDispatchResult:
        if engine_name not in self._engines:
            raise KeyError(f"STRATEGY_ENGINE_NOT_REGISTERED engine_name={engine_name}")

        return StrategyDispatchResult(
            strategy_code=strategy_code,
            engine_name=engine_name,
            engine_version=engine_version,
            engine=self._engines[engine_name],
        )

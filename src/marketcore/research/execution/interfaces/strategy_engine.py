from __future__ import annotations

from typing import Protocol

from marketcore.research.execution.dto.signal import StrategySignal
from marketcore.research.execution.interfaces.data_provider import MarketBars


class StrategyEngine(Protocol):
    engine_name: str

    def execute(
        self,
        market_data: MarketBars,
        parameters: dict | None = None,
    ) -> list[StrategySignal]:
        ...

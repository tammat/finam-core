from __future__ import annotations

from typing import Protocol

from marketcore.research.execution.dto.research_trade import ResearchTrade
from marketcore.research.execution.dto.signal import StrategySignal
from marketcore.research.execution.interfaces.data_provider import MarketBars


class TradeGenerator(Protocol):
    generator_name: str
    generator_version: str

    def run(
        self,
        market_data: MarketBars,
        signals: list[StrategySignal],
        parameters: dict | None = None,
    ) -> list[ResearchTrade]:
        ...

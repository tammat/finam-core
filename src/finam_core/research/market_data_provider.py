from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Protocol


@dataclass(frozen=True, slots=True)
class ResearchBar:
    symbol: str
    timeframe: str
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str
    asset_class: str


class ResearchMarketDataProvider(Protocol):
    name: str
    asset_classes: tuple[str, ...]

    def fetch_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> Iterable[ResearchBar]:
        ...


class ProviderNotImplementedError(NotImplementedError):
    pass


class BaseResearchProvider:
    name = "base"
    asset_classes: tuple[str, ...] = ()

    def fetch_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> Iterable[ResearchBar]:
        raise ProviderNotImplementedError(
            f"provider={self.name} does not implement fetch_bars yet"
        )


class BinanceResearchProvider(BaseResearchProvider):
    name = "binance"
    asset_classes = ("crypto",)


class PolygonResearchProvider(BaseResearchProvider):
    name = "polygon_massive"
    asset_classes = ("us_etf", "us_equity")


class AlphaVantageResearchProvider(BaseResearchProvider):
    name = "alpha_vantage"
    asset_classes = ("us_etf", "us_equity", "fx")


class TwelveDataResearchProvider(BaseResearchProvider):
    name = "twelve_data"
    asset_classes = ("fx", "crypto", "us_etf", "us_equity")


class DailyFallbackResearchProvider(BaseResearchProvider):
    name = "daily_fallback"
    asset_classes = ("us_etf", "fx")


def provider_candidates_for_asset_class(asset_class: str) -> list[BaseResearchProvider]:
    providers: list[BaseResearchProvider] = [
        BinanceResearchProvider(),
        PolygonResearchProvider(),
        AlphaVantageResearchProvider(),
        TwelveDataResearchProvider(),
        DailyFallbackResearchProvider(),
    ]

    return [p for p in providers if asset_class in p.asset_classes]


def recommended_provider_name(asset_class: str) -> str:
    mapping = {
        "crypto": "binance",
        "us_etf": "polygon_massive",
        "fx": "twelve_data",
    }
    return mapping.get(asset_class, "daily_fallback")

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Protocol
import json
import urllib.parse
import urllib.request


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
        BinancePublicKlinesResearchProvider(),
        BinanceResearchProvider(),
        PolygonResearchProvider(),
        AlphaVantageResearchProvider(),
        TwelveDataResearchProvider(),
        DailyFallbackResearchProvider(),
    ]

    return [p for p in providers if asset_class in p.asset_classes]


def recommended_provider_name(asset_class: str) -> str:
    mapping = {
        "crypto": "binance_public_klines",
        "us_etf": "polygon_massive",
        "fx": "twelve_data",
    }
    return mapping.get(asset_class, "daily_fallback")


class BinancePublicKlinesResearchProvider(BinanceResearchProvider):
    name = "binance_public_klines"
    base_url = "https://api.binance.com/api/v3/klines"

    _symbol_map = {
        "BTCUSD": "BTCUSDT",
        "ETHUSD": "ETHUSDT",
        "BTCUSDT": "BTCUSDT",
        "ETHUSDT": "ETHUSDT",
    }

    _timeframe_map = {
        "M1": "1m",
        "M5": "5m",
        "M15": "15m",
        "1m": "1m",
        "5m": "5m",
        "15m": "15m",
    }

    def _normalize_symbol(self, symbol: str) -> str:
        key = symbol.upper()
        if key not in self._symbol_map:
            raise ValueError(f"unsupported_binance_symbol={symbol}")
        return self._symbol_map[key]

    def _normalize_timeframe(self, timeframe: str) -> str:
        key = timeframe.upper()
        if key not in self._timeframe_map:
            raise ValueError(f"unsupported_binance_timeframe={timeframe}")
        return self._timeframe_map[key]

    def fetch_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> Iterable[ResearchBar]:
        if start >= end:
            return []

        binance_symbol = self._normalize_symbol(symbol)
        interval = self._normalize_timeframe(timeframe)

        all_bars: list[ResearchBar] = []
        current_start_ms = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)

        while current_start_ms < end_ms:
            params = {
                "symbol": binance_symbol,
                "interval": interval,
                "startTime": current_start_ms,
                "endTime": end_ms,
                "limit": 1000,
            }

            url = self.base_url + "?" + urllib.parse.urlencode(params)

            with urllib.request.urlopen(url, timeout=20) as response:
                raw = response.read().decode("utf-8")

            data = json.loads(raw)
            if not data:
                break

            last_open_time_ms = None

            for item in data:
                open_time_ms = int(item[0])
                last_open_time_ms = open_time_ms

                all_bars.append(
                    ResearchBar(
                        symbol=symbol.upper(),
                        timeframe=timeframe.upper(),
                        ts=datetime.fromtimestamp(open_time_ms / 1000, tz=start.tzinfo),
                        open=float(item[1]),
                        high=float(item[2]),
                        low=float(item[3]),
                        close=float(item[4]),
                        volume=float(item[5]),
                        source=self.name,
                        asset_class="crypto",
                    )
                )

            if last_open_time_ms is None:
                break

            next_start_ms = last_open_time_ms + 1
            if next_start_ms <= current_start_ms:
                break

            current_start_ms = next_start_ms

            if len(data) < 1000:
                break

        # Защита от возможных дублей на границах страниц.
        dedup: dict[datetime, ResearchBar] = {}
        for bar in all_bars:
            dedup[bar.ts] = bar

        return [dedup[k] for k in sorted(dedup)]


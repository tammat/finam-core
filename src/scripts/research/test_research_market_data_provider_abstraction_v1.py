#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone

from finam_core.research.market_data_provider import (
    BinanceResearchProvider,
    ProviderNotImplementedError,
    ResearchBar,
    provider_candidates_for_asset_class,
    recommended_provider_name,
)


def main() -> None:
    bar = ResearchBar(
        symbol="BTCUSD",
        timeframe="M1",
        ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
        open=1.0,
        high=2.0,
        low=0.5,
        close=1.5,
        volume=100.0,
        source="test",
        asset_class="crypto",
    )

    assert bar.symbol == "BTCUSD"
    assert bar.timeframe == "M1"
    assert bar.source == "test"

    crypto = provider_candidates_for_asset_class("crypto")
    assert any(p.name == "binance" for p in crypto)

    etf = provider_candidates_for_asset_class("us_etf")
    assert any(p.name == "polygon_massive" for p in etf)
    assert any(p.name == "alpha_vantage" for p in etf)

    fx = provider_candidates_for_asset_class("fx")
    assert any(p.name == "twelve_data" for p in fx)

    assert recommended_provider_name("crypto") == "binance"
    assert recommended_provider_name("us_etf") == "polygon_massive"
    assert recommended_provider_name("fx") == "twelve_data"

    provider = BinanceResearchProvider()
    try:
        list(
            provider.fetch_bars(
                symbol="BTCUSD",
                timeframe="M1",
                start=datetime(2026, 1, 1, tzinfo=timezone.utc),
                end=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
        )
    except ProviderNotImplementedError:
        pass
    else:
        raise AssertionError("BinanceResearchProvider must be abstraction-only in v1")

    print("RESEARCH_MARKET_DATA_PROVIDER_ABSTRACTION_V1_OK")


if __name__ == "__main__":
    main()

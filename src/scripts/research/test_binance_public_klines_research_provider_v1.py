#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from finam_core.research.market_data_provider import (
    BinancePublicKlinesResearchProvider,
    provider_candidates_for_asset_class,
    recommended_provider_name,
)


def main() -> None:
    provider = BinancePublicKlinesResearchProvider()

    assert provider._normalize_symbol("BTCUSD") == "BTCUSDT"
    assert provider._normalize_symbol("ETHUSD") == "ETHUSDT"
    assert provider._normalize_timeframe("M1") == "1m"
    assert provider._normalize_timeframe("M5") == "5m"
    assert provider._normalize_timeframe("M15") == "15m"

    crypto = provider_candidates_for_asset_class("crypto")
    assert any(p.name == "binance_public_klines" for p in crypto)
    assert recommended_provider_name("crypto") == "binance_public_klines"

    # Короткая research-only smoke-проверка публичного market data endpoint.
    end = datetime.now(timezone.utc) - timedelta(days=1)
    start = end - timedelta(minutes=10)

    bars = list(provider.fetch_bars("BTCUSD", "M1", start, end))

    assert len(bars) > 0
    assert bars[0].symbol == "BTCUSD"
    assert bars[0].timeframe == "M1"
    assert bars[0].source == "binance_public_klines"
    assert bars[0].asset_class == "crypto"
    assert bars[0].high >= bars[0].low

    print(f"BINANCE_PUBLIC_KLINES_RESEARCH_PROVIDER_V1_OK bars={len(bars)}")


if __name__ == "__main__":
    main()

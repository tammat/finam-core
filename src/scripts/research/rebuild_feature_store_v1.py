#!/usr/bin/env python3
from __future__ import annotations

import argparse

from finam_core.research.feature_store import ResearchFeatureStoreBuilder


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", default="BRN6@RTSX,NGN6@RTSX,USDRUBF@RTSX,BTCUSD,ETHUSD")
    parser.add_argument("--timeframes", default="M1,M5")
    parser.add_argument("--limit", type=int, default=5000)
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    timeframes = [t.strip() for t in args.timeframes.split(",") if t.strip()]

    builder = ResearchFeatureStoreBuilder()
    builder.ensure_schema()

    print("=== REBUILD FEATURE STORE V1 ===")
    total_written = 0

    for symbol in symbols:
        for timeframe in timeframes:
            result = builder.rebuild_symbol_timeframe(symbol, timeframe, args.limit)
            total_written += result.rows_written
            print(
                f"FEATURE_BUILD_ROW symbol={result.symbol} timeframe={result.timeframe} "
                f"bars_seen={result.bars_seen} rows_written={result.rows_written}"
            )

    print(f"TOTAL_ROWS_WRITTEN={total_written}")
    print("VERDICT=OK")


if __name__ == "__main__":
    main()

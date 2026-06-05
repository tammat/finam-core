#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from finam_core.research.market_data_provider import BinancePublicKlinesResearchProvider
from finam_core.research.market_bars_ingestion import ResearchMarketBarsIngestor


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", default="BTCUSD,ETHUSD")
    parser.add_argument("--timeframes", default="M1,M5")
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    timeframes = [t.strip().upper() for t in args.timeframes.split(",") if t.strip()]

    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=args.hours)

    provider = BinancePublicKlinesResearchProvider()
    ingestor = ResearchMarketBarsIngestor()

    print("=== BINANCE CRYPTO BACKFILL V1 ===")
    print(f"mode={'APPLY' if args.apply else 'DRY_RUN'}")
    print(f"symbols={','.join(symbols)}")
    print(f"timeframes={','.join(timeframes)}")
    print(f"start={start.isoformat()}")
    print(f"end={end.isoformat()}")
    print()

    total_seen = 0
    total_written = 0

    for symbol in symbols:
        for timeframe in timeframes:
            bars = list(provider.fetch_bars(symbol, timeframe, start, end))
            total_seen += len(bars)

            written = 0
            if args.apply:
                result = ingestor.ingest(bars)
                written = result.rows_written
                total_written += written

            first_ts = bars[0].ts.isoformat() if bars else "None"
            last_ts = bars[-1].ts.isoformat() if bars else "None"

            print(
                f"BACKFILL_ROW symbol={symbol} timeframe={timeframe} "
                f"bars={len(bars)} written={written} "
                f"first_ts={first_ts} last_ts={last_ts}"
            )

    print()
    print(f"TOTAL_BARS_SEEN={total_seen}")
    print(f"TOTAL_BARS_WRITTEN={total_written}")
    print(f"VERDICT={'APPLIED' if args.apply else 'DRY_RUN'}")


if __name__ == "__main__":
    main()

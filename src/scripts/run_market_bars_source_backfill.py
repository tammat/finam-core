from __future__ import annotations

import os
from datetime import datetime, timedelta, UTC

from finam_core.data.market_bars_source import (
    MarketBar,
    MarketBarsSource,
)


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    symbol = os.getenv("BARS_SYMBOL", "SBER@MISX").strip().upper()
    timeframe = os.getenv("BARS_TIMEFRAME", "M5").strip().upper()

    source = MarketBarsSource(dsn)
    source.ensure_schema()

    now = datetime.now(UTC)

    price = 320.0

    inserted = 0

    for i in range(120):
        ts = now - timedelta(minutes=(120 - i) * 5)

        drift = i * 0.20

        open_price = price + drift
        close_price = open_price + 0.05
        high_price = close_price + 0.02
        low_price = open_price - 0.02

        source.insert_bar(
            MarketBar(
                symbol=symbol,
                timeframe=timeframe,
                ts=ts,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=1000 + i,
            )
        )

        inserted += 1

    print(
        f"MARKET_BARS_BACKFILL_OK symbol={symbol} "
        f"timeframe={timeframe} inserted={inserted}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

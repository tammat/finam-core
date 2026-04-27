# -*- coding: utf-8 -*-
# Русский коммент: загрузка исторических свечей через HistoryLoader.
# Контракт: HistoryLoader.load(symbol, timeframe, start, end)

import os
from datetime import datetime, timedelta, timezone

from finam_core.ingestion.history_loader import HistoryLoader


def main() -> None:
    symbol = os.getenv("SYMBOL") or "NGH6@RTSX"
    timeframe = os.getenv("TIMEFRAME") or os.getenv("INTERVAL") or "M5"
    lookback_days = int(os.getenv("LOOKBACK_DAYS") or "30")

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback_days)

    loader = HistoryLoader()
    bars = loader.load(symbol, timeframe, start, end)

    print(f"OK: loaded bars={len(bars)} symbol={symbol} tf={timeframe}", flush=True)
    for row in bars[:3]:
        print(row, flush=True)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import time
from datetime import datetime, timedelta, timezone

from finam_core.ingestion.bars_client import FinamBarsClient
from finam_core.ingestion.history_loader import HistoryBar, HistoryLoader


def parse_ts(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    ts = datetime.fromisoformat(text)
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def get_attr(obj, *names):
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


def as_float(value) -> float | None:
    if value is None:
        return None
    if hasattr(value, "value"):
        return float(value.value)
    return float(value)


def as_dt(value) -> datetime:
    if hasattr(value, "ToDatetime"):
        return value.ToDatetime().replace(tzinfo=timezone.utc)
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    raise ValueError(f"Unsupported timestamp: {value!r}")


def normalize_response(response, symbol: str, timeframe: str) -> list[HistoryBar]:
    raw_bars = get_attr(response, "bars", "candles", "data")
    if raw_bars is None:
        try:
            raw_bars = list(response)
        except TypeError:
            raw_bars = []

    bars: list[HistoryBar] = []

    for b in raw_bars:
        ts_raw = get_attr(b, "timestamp", "ts", "time", "date_time")
        open_raw = get_attr(b, "open", "open_price")
        high_raw = get_attr(b, "high", "high_price")
        low_raw = get_attr(b, "low", "low_price")
        close_raw = get_attr(b, "close", "close_price")
        volume_raw = get_attr(b, "volume", "vol")

        close_price = as_float(close_raw)
        if close_price is None:
            continue

        bars.append(
            HistoryBar(
                symbol=symbol,
                timeframe=timeframe,
                ts=as_dt(ts_raw),
                open=as_float(open_raw),
                high=as_float(high_raw),
                low=as_float(low_raw),
                close_price=close_price,
                volume=float(as_float(volume_raw) or 0.0),
            )
        )

    return bars
def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="BRM6@RTSX")
    p.add_argument("--timeframe", default="M1")
    p.add_argument("--from-ts", required=True)
    p.add_argument("--to-ts", required=True)
    p.add_argument("--chunk-minutes", type=int, default=180)
    p.add_argument("--sleep-sec", type=float, default=1.0)
    args = p.parse_args()

    start = parse_ts(args.from_ts)
    end = parse_ts(args.to_ts)

    client = FinamBarsClient()
    loader = HistoryLoader()

    total = 0
    cur = start

    try:
        while cur < end:
            nxt = min(end, cur + timedelta(minutes=args.chunk_minutes))
            print(f"FETCH {args.symbol} {args.timeframe} {cur.isoformat()}..{nxt.isoformat()}", flush=True)

            response = client.get_bars(args.symbol, args.timeframe, cur, nxt)
            bars = normalize_response(response, args.symbol, args.timeframe)
            written = loader.load_bars(bars)

            total += written
            print(f"got={len(bars)} written={written} total={total}", flush=True)

            cur = nxt
            if args.sleep_sec > 0:
                time.sleep(args.sleep_sec)

    finally:
        client.close()

    print(f"OK: loaded {total} bars into market_data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

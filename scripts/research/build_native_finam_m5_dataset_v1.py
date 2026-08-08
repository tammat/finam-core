#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from finam_core.ingestion.bars_client import FinamBarsClient
from finam_core.research.versioned_market_bars_v1 import (
    NATIVE_FINAM_M5_V1,
    VersionedResearchBar,
    build_bar,
)


SOURCE_VERSION = "NATIVE_FINAM_M5_DATASET_BUILDER_V1"
PROVIDER = "FINAM_GRPC"
PROVIDER_DATA_VERSION = "FINAM_NATIVE_M5_V1"

DEFAULT_SYMBOL = "NGU6@RTSX"
DEFAULT_TIMEFRAME = "M5"


def parse_ts(value: str) -> datetime:
    result = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if result.tzinfo is None:
        raise ValueError(
            "timestamp_must_be_timezone_aware"
        )

    return result.astimezone(timezone.utc)


def proto_ts(bar) -> datetime:
    value = (
        getattr(bar, "timestamp", None)
        or getattr(bar, "time", None)
    )

    if value is None:
        raise RuntimeError(
            "finam_bar_timestamp_missing"
        )

    if hasattr(value, "ToDatetime"):
        result = value.ToDatetime()
    else:
        result = value

    if result.tzinfo is None:
        result = result.replace(
            tzinfo=timezone.utc
        )

    return result.astimezone(timezone.utc)


def decimal_value(value) -> Decimal:
    if hasattr(value, "value"):
        value = value.value

    return Decimal(str(value))


def convert_bar(
    bar,
    *,
    dataset_version: str,
    symbol: str,
    timeframe: str,
) -> VersionedResearchBar:
    return build_bar(
        dataset_version=dataset_version,
        symbol=symbol,
        timeframe=timeframe,
        ts=proto_ts(bar),
        open=decimal_value(bar.open),
        high=decimal_value(bar.high),
        low=decimal_value(bar.low),
        close=decimal_value(bar.close),
        volume=decimal_value(
            getattr(bar, "volume", 0) or 0
        ),
        provider=PROVIDER,
        provider_data_version=PROVIDER_DATA_VERSION,
    )


def merge_chunk_bars(
    chunks: list[list[VersionedResearchBar]],
) -> list[VersionedResearchBar]:
    merged: dict[datetime, VersionedResearchBar] = {}

    for chunk in chunks:
        for bar in chunk:
            existing = merged.get(bar.ts)

            if existing is None:
                merged[bar.ts] = bar
                continue

            if (
                existing.source_payload_hash
                != bar.source_payload_hash
            ):
                raise RuntimeError(
                    "native_finam_chunk_overlap_conflict:"
                    f"{bar.ts.isoformat()}"
                )

    return [
        merged[ts]
        for ts in sorted(merged)
    ]


def fetch_chunked_bars(
    client: FinamBarsClient,
    *,
    dataset_version: str,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
    chunk_days: int,
) -> tuple[list[VersionedResearchBar], int]:
    if chunk_days <= 0:
        raise RuntimeError(
            "chunk_days_must_be_positive"
        )

    chunks: list[list[VersionedResearchBar]] = []
    request_count = 0

    cursor = start

    while cursor < end:
        chunk_end = min(
            end,
            cursor + timedelta(days=chunk_days),
        )

        response = client.get_bars(
            symbol=symbol,
            timeframe=timeframe,
            start=cursor,
            end=chunk_end,
        )

        raw = list(
            getattr(response, "bars", [])
            or []
        )

        chunks.append(
            [
                convert_bar(
                    bar,
                    dataset_version=dataset_version,
                    symbol=symbol,
                    timeframe=timeframe,
                )
                for bar in raw
            ]
        )

        request_count += 1
        cursor = chunk_end

    return (
        merge_chunk_bars(chunks),
        request_count,
    )


def dataset_fingerprint(
    bars: list[VersionedResearchBar],
) -> str:
    digest = hashlib.sha256()

    for bar in bars:
        digest.update(
            (
                f"{bar.dataset_version}|"
                f"{bar.symbol}|"
                f"{bar.timeframe}|"
                f"{bar.ts.isoformat()}|"
                f"{bar.source_payload_hash}\n"
            ).encode("utf-8")
        )

    return digest.hexdigest()


def validate_dataset(
    bars: list[VersionedResearchBar],
    *,
    start: datetime,
    end: datetime,
) -> None:
    if not bars:
        raise RuntimeError(
            "native_finam_dataset_empty"
        )

    timestamps = [
        bar.ts
        for bar in bars
    ]

    if timestamps != sorted(timestamps):
        raise RuntimeError(
            "native_finam_dataset_not_sorted"
        )

    if len(timestamps) != len(set(timestamps)):
        raise RuntimeError(
            "native_finam_dataset_duplicate_timestamp"
        )

    if timestamps[0] < start:
        raise RuntimeError(
            "native_finam_dataset_before_requested_start"
        )

    if timestamps[-1] > end:
        raise RuntimeError(
            "native_finam_dataset_after_requested_end"
        )


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--symbol",
        default=DEFAULT_SYMBOL,
    )
    parser.add_argument(
        "--timeframe",
        default=DEFAULT_TIMEFRAME,
    )
    parser.add_argument(
        "--start",
        required=True,
    )
    parser.add_argument(
        "--end",
        required=True,
    )
    parser.add_argument(
        "--dataset-version",
        default=NATIVE_FINAM_M5_V1,
    )
    parser.add_argument(
        "--chunk-days",
        type=int,
        default=7,
    )
    parser.add_argument(
        "--write",
        action="store_true",
    )

    args = parser.parse_args()

    if args.write:
        raise RuntimeError(
            "write_mode_not_implemented"
        )

    start = parse_ts(args.start)
    end = parse_ts(args.end)

    if start >= end:
        raise RuntimeError(
            "invalid_dataset_time_range"
        )

    client = FinamBarsClient()

    try:
        bars, request_count = fetch_chunked_bars(
            client,
            dataset_version=args.dataset_version,
            symbol=args.symbol,
            timeframe=args.timeframe,
            start=start,
            end=end,
            chunk_days=args.chunk_days,
        )

    finally:
        client.close()

    validate_dataset(
        bars,
        start=start,
        end=end,
    )

    fingerprint = dataset_fingerprint(bars)

    print("=== NATIVE FINAM M5 DATASET V1 ===")
    print(f"dataset_version={args.dataset_version}")
    print(f"symbol={args.symbol}")
    print(f"timeframe={args.timeframe}")
    print(f"requested_start={start.isoformat()}")
    print(f"requested_end={end.isoformat()}")
    print(f"chunk_days={args.chunk_days}")
    print(f"request_count={request_count}")
    print(f"bar_count={len(bars)}")
    print(f"first_bar={bars[0].ts.isoformat()}")
    print(f"last_bar={bars[-1].ts.isoformat()}")
    print(f"provider={PROVIDER}")
    print(
        f"provider_data_version="
        f"{PROVIDER_DATA_VERSION}"
    )
    print(f"dataset_fingerprint={fingerprint}")

    print()
    print("=== FIRST 5 ===")
    for bar in bars[:5]:
        print(
            bar.ts,
            bar.open,
            bar.high,
            bar.low,
            bar.close,
            bar.volume,
            bar.source_payload_hash,
        )

    print()
    print("=== LAST 5 ===")
    for bar in bars[-5:]:
        print(
            bar.ts,
            bar.open,
            bar.high,
            bar.low,
            bar.close,
            bar.volume,
            bar.source_payload_hash,
        )

    print()
    print("DATABASE_WRITE=NO")
    print("PARAMETER_SEARCH=NO")
    print("ADAPTER_CHANGED=0")
    print(
        "VERDICT="
        "NATIVE_FINAM_M5_DATASET_V1_DRY_RUN_OK"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

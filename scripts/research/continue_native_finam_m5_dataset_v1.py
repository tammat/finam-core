#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import sys
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.ingestion.bars_client import FinamBarsClient
from dataclasses import dataclass

from finam_core.research.versioned_market_bars_ingestion_v1 import (
    ingest_many,
)
from finam_core.research.versioned_market_bars_v1 import (
    VersionedResearchBar,
)


SOURCE_VERSION = "NATIVE_FINAM_M5_CONTINUATION_V1"


EXPECTED_PREFIX_COUNT = 7568
EXPECTED_PREFIX_LAST = datetime(
    2026, 8, 8, 11, 0,
    tzinfo=timezone.utc,
)
EXPECTED_PREFIX_FINGERPRINT = (
    "bea4694b70b87c6ccbdf1594eec235a25"
    "dd1b90948a0a83eb5fc43b3ea8abd1f"
)

REFERENCE_BUILDER_PATH = (
    Path(__file__).resolve().parent
    / "build_native_finam_m5_dataset_v1.py"
)


def load_reference_builder():
    spec = importlib.util.spec_from_file_location(
        "native_finam_m5_continuation_reference",
        REFERENCE_BUILDER_PATH,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "reference_builder_import_failed"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    return module


def verify_base_prefix_anchor(
    bars: list[VersionedResearchBar],
    *,
    base_last: datetime,
    base_count: int,
    base_fingerprint: str,
    fingerprint_fn,
) -> None:
    base_prefix = [
        bar
        for bar in bars
        if bar.ts <= base_last
    ]

    if len(base_prefix) != base_count:
        raise RuntimeError(
            "base_prefix_count_mismatch:"
            f"actual={len(base_prefix)}:"
            f"expected={base_count}"
        )

    actual_fingerprint = fingerprint_fn(
        base_prefix
    )

    if actual_fingerprint != base_fingerprint:
        raise RuntimeError(
            "base_prefix_fingerprint_mismatch:"
            f"expected={base_fingerprint}:"
            f"actual={actual_fingerprint}"
        )


def load_persisted_dataset_snapshot():
    reference = load_reference_builder()

    with psycopg2.connect(
        build_psycopg_url()
    ) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:
            bars = reference.load_persisted_dataset(
                cur,
                dataset_version=EXPECTED_DATASET_VERSION,
                symbol=EXPECTED_SYMBOL,
                timeframe=EXPECTED_TIMEFRAME,
            )

    if not bars:
        raise RuntimeError(
            "persisted_dataset_empty"
        )

    validate_candidate_identity(bars)
    validate_candidate_ordering(bars)

    # Permanent immutable historical anchor.
    # Rows after EXPECTED_PREFIX_LAST may grow append-only.
    verify_base_prefix_anchor(
        bars,
        base_last=EXPECTED_PREFIX_LAST,
        base_count=EXPECTED_PREFIX_COUNT,
        base_fingerprint=EXPECTED_PREFIX_FINGERPRINT,
        fingerprint_fn=reference.dataset_fingerprint,
    )

    return bars



@dataclass(frozen=True, slots=True)
class ContinuationClassification:
    overlap_identical: int
    new_rows: int
    suffix: list[VersionedResearchBar]


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
                f"{bar.open}|"
                f"{bar.high}|"
                f"{bar.low}|"
                f"{bar.close}|"
                f"{bar.volume}|"
                f"{bar.provider}|"
                f"{bar.provider_data_version}|"
                f"{bar.source_payload_hash}\n"
            ).encode("utf-8")
        )

    return digest.hexdigest()


EXPECTED_DATASET_VERSION = "NATIVE_FINAM_M5_V1"
EXPECTED_SYMBOL = "NGU6@RTSX"
EXPECTED_TIMEFRAME = "M5"
EXPECTED_PROVIDER = "FINAM_GRPC"
EXPECTED_PROVIDER_DATA_VERSION = "FINAM_NATIVE_M5_V1"


def validate_candidate_identity(
    bars: list[VersionedResearchBar],
) -> None:
    expected = (
        EXPECTED_DATASET_VERSION,
        EXPECTED_SYMBOL,
        EXPECTED_TIMEFRAME,
        EXPECTED_PROVIDER,
        EXPECTED_PROVIDER_DATA_VERSION,
    )

    for bar in bars:
        actual = (
            bar.dataset_version,
            bar.symbol,
            bar.timeframe,
            bar.provider,
            bar.provider_data_version,
        )

        if actual != expected:
            raise RuntimeError(
                "continuation_identity_mismatch:"
                f"ts={bar.ts.isoformat()}:"
                f"actual={actual}:"
                f"expected={expected}"
            )


def validate_candidate_ordering(
    bars: list[VersionedResearchBar],
) -> None:
    for previous, current in zip(
        bars,
        bars[1:],
    ):
        if current.ts <= previous.ts:
            raise RuntimeError(
                "continuation_candidate_not_strictly_ordered:"
                f"previous={previous.ts.isoformat()}:"
                f"current={current.ts.isoformat()}"
            )


def continuation_overlap_start(
    persisted_last: datetime,
    *,
    overlap_days: int,
) -> datetime:
    if overlap_days <= 0:
        raise RuntimeError(
            "overlap_days_must_be_positive"
        )

    return (
        persisted_last
        - timedelta(days=overlap_days)
    )


def verify_prefix_fingerprint(
    prefix: list[VersionedResearchBar],
    expected_fingerprint: str,
) -> str:
    actual = dataset_fingerprint(prefix)

    if actual != expected_fingerprint:
        raise RuntimeError(
            "historical_prefix_fingerprint_mismatch:"
            f"expected={expected_fingerprint}:"
            f"actual={actual}"
        )

    return actual


def classify_continuation(
    persisted: list[VersionedResearchBar],
    candidate: list[VersionedResearchBar],
) -> ContinuationClassification:
    if not persisted:
        raise RuntimeError(
            "continuation_requires_persisted_dataset"
        )

    persisted_by_ts = {
        bar.ts: bar
        for bar in persisted
    }

    if len(persisted_by_ts) != len(persisted):
        raise RuntimeError(
            "persisted_dataset_duplicate_timestamp"
        )

    persisted_last = persisted[-1].ts

    overlap_identical = 0
    suffix: list[VersionedResearchBar] = []

    seen_candidate_ts = set()

    for bar in candidate:
        if bar.ts in seen_candidate_ts:
            raise RuntimeError(
                "continuation_candidate_duplicate_timestamp:"
                f"{bar.ts.isoformat()}"
            )

        seen_candidate_ts.add(bar.ts)

        existing = persisted_by_ts.get(bar.ts)

        if existing is not None:
            if (
                existing.source_payload_hash
                != bar.source_payload_hash
            ):
                raise RuntimeError(
                    "continuation_historical_conflict:"
                    f"{bar.ts.isoformat()}"
                )

            overlap_identical += 1
            continue

        if bar.ts <= persisted_last:
            raise RuntimeError(
                "continuation_unknown_historical_timestamp:"
                f"{bar.ts.isoformat()}"
            )

        suffix.append(bar)

    suffix.sort(key=lambda bar: bar.ts)

    return ContinuationClassification(
        overlap_identical=overlap_identical,
        new_rows=len(suffix),
        suffix=suffix,
    )



def persist_continuation(
    suffix: list[VersionedResearchBar],
    *,
    expected_prefix_count: int,
    expected_prefix_last: datetime,
    expected_prefix_fingerprint: str,
):
    if not suffix:
        raise RuntimeError(
            "continuation_write_requires_new_rows"
        )

    validate_candidate_identity(suffix)
    validate_candidate_ordering(suffix)

    if any(
        bar.ts <= expected_prefix_last
        for bar in suffix
    ):
        raise RuntimeError(
            "continuation_suffix_not_strictly_new"
        )

    reference = load_reference_builder()

    candidate_suffix_fingerprint = (
        reference.dataset_fingerprint(suffix)
    )

    connection = psycopg2.connect(
        build_psycopg_url()
    )

    try:
        connection.autocommit = False

        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:

            before = reference.load_persisted_dataset(
                cursor,
                dataset_version=EXPECTED_DATASET_VERSION,
                symbol=EXPECTED_SYMBOL,
                timeframe=EXPECTED_TIMEFRAME,
            )

            if len(before) != expected_prefix_count:
                raise RuntimeError(
                    "continuation_prewrite_count_changed:"
                    f"actual={len(before)}:"
                    f"expected={expected_prefix_count}"
                )

            if not before:
                raise RuntimeError(
                    "continuation_prewrite_dataset_empty"
                )

            if before[-1].ts != expected_prefix_last:
                raise RuntimeError(
                    "continuation_prewrite_tail_changed:"
                    f"actual={before[-1].ts.isoformat()}:"
                    f"expected={expected_prefix_last.isoformat()}"
                )

            prefix_fingerprint = (
                reference.dataset_fingerprint(before)
            )

            if (
                prefix_fingerprint
                != expected_prefix_fingerprint
            ):
                raise RuntimeError(
                    "continuation_prewrite_prefix_changed:"
                    f"{prefix_fingerprint}"
                )

            result = ingest_many(
                cursor,
                suffix,
            )

            if result.rows_seen != len(suffix):
                raise RuntimeError(
                    "continuation_rows_seen_mismatch"
                )

            if result.rows_inserted != len(suffix):
                raise RuntimeError(
                    "continuation_rows_inserted_mismatch:"
                    f"{result.rows_inserted}:"
                    f"expected={len(suffix)}"
                )

            if result.rows_identical != 0:
                raise RuntimeError(
                    "continuation_unexpected_identical_rows:"
                    f"{result.rows_identical}"
                )

            extended = reference.load_persisted_dataset(
                cursor,
                dataset_version=EXPECTED_DATASET_VERSION,
                symbol=EXPECTED_SYMBOL,
                timeframe=EXPECTED_TIMEFRAME,
            )

            expected_count = (
                expected_prefix_count
                + len(suffix)
            )

            if len(extended) != expected_count:
                raise RuntimeError(
                    "continuation_postwrite_count_mismatch:"
                    f"{len(extended)}:"
                    f"expected={expected_count}"
                )

            extended_prefix = [
                bar
                for bar in extended
                if bar.ts <= expected_prefix_last
            ]

            if (
                reference.dataset_fingerprint(
                    extended_prefix
                )
                != expected_prefix_fingerprint
            ):
                raise RuntimeError(
                    "continuation_prefix_changed_during_write"
                )

            persisted_suffix = [
                bar
                for bar in extended
                if bar.ts > expected_prefix_last
            ]

            persisted_suffix_fingerprint = (
                reference.dataset_fingerprint(
                    persisted_suffix
                )
            )

            if (
                persisted_suffix_fingerprint
                != candidate_suffix_fingerprint
            ):
                raise RuntimeError(
                    "continuation_suffix_fingerprint_mismatch"
                )

            extended_fingerprint = (
                reference.dataset_fingerprint(
                    extended
                )
            )

        connection.commit()

        return (
            result,
            candidate_suffix_fingerprint,
            extended_fingerprint,
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Dry-run continuation contract for "
            "NATIVE_FINAM_M5_V1"
        )
    )

    parser.add_argument(
        "--overlap-days",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--chunk-days",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--write",
        action="store_true",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.overlap_days <= 0:
        raise RuntimeError(
            "overlap_days_must_be_positive"
        )

    if args.chunk_days <= 0:
        raise RuntimeError(
            "chunk_days_must_be_positive"
        )

    reference = load_reference_builder()
    persisted = load_persisted_dataset_snapshot()

    persisted_last = persisted[-1].ts
    persisted_prefix_count = len(persisted)
    persisted_prefix_fingerprint = (
        reference.dataset_fingerprint(persisted)
    )

    request_start = continuation_overlap_start(
        persisted_last,
        overlap_days=args.overlap_days,
    )

    request_end = datetime.now(timezone.utc)

    if request_end <= persisted_last:
        raise RuntimeError(
            "continuation_request_end_not_after_persisted_tail"
        )

    client = FinamBarsClient()

    candidate, request_count = (
        reference.fetch_chunked_bars(
            client,
            dataset_version=EXPECTED_DATASET_VERSION,
            symbol=EXPECTED_SYMBOL,
            timeframe=EXPECTED_TIMEFRAME,
            start=request_start,
            end=request_end,
            chunk_days=args.chunk_days,
        )
    )

    validate_candidate_identity(candidate)
    validate_candidate_ordering(candidate)

    classification = classify_continuation(
        persisted,
        candidate,
    )

    print("=== CONTINUATION PREFLIGHT ===")
    print("persisted_rows =", len(persisted))
    print("persisted_last =", persisted_last)
    print("request_start =", request_start)
    print("request_end =", request_end)
    print("request_count =", request_count)
    print(
        "overlap_identical =",
        classification.overlap_identical,
    )
    print(
        "new_rows =",
        classification.new_rows,
    )

    if classification.suffix:
        print(
            "suffix_first =",
            classification.suffix[0].ts,
        )
        print(
            "suffix_last =",
            classification.suffix[-1].ts,
        )
        print(
            "suffix_fingerprint =",
            reference.dataset_fingerprint(
                classification.suffix
            ),
        )

    if not args.write:
        print("DATABASE_WRITE=NO")
        print(
            "VERDICT="
            + (
                "NATIVE_FINAM_M5_CONTINUATION_SUFFIX_READY"
                if classification.new_rows
                else
                "NATIVE_FINAM_M5_CONTINUATION_NO_NEW_DATA"
            )
        )
        return 0

    if classification.new_rows == 0:
        print("DATABASE_WRITE=NO")
        print(
            "VERDICT="
            "NATIVE_FINAM_M5_CONTINUATION_NO_NEW_DATA"
        )
        return 0

    (
        result,
        suffix_fingerprint,
        extended_fingerprint,
    ) = persist_continuation(
        classification.suffix,
        expected_prefix_count=persisted_prefix_count,
        expected_prefix_last=persisted_last,
        expected_prefix_fingerprint=(
            persisted_prefix_fingerprint
        ),
    )

    print()
    print("=== PERSISTENCE ===")
    print("rows_seen =", result.rows_seen)
    print(
        "rows_inserted =",
        result.rows_inserted,
    )
    print(
        "rows_identical =",
        result.rows_identical,
    )
    print(
        "suffix_fingerprint =",
        suffix_fingerprint,
    )
    print(
        "extended_fingerprint =",
        extended_fingerprint,
    )
    print("DATABASE_WRITE=YES")
    print(
        "VERDICT="
        "NATIVE_FINAM_M5_CONTINUATION_PERSISTED"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

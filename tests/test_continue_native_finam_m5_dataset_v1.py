from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from finam_core.research.versioned_market_bars_v1 import (
    NATIVE_FINAM_M5_V1,
    VersionedResearchBar,
    build_bar,
)


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts/research/continue_native_finam_m5_dataset_v1.py"
)

SPEC = importlib.util.spec_from_file_location(
    "continue_native_finam_m5_dataset_test",
    SCRIPT,
)
assert SPEC is not None
assert SPEC.loader is not None

builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)


def ts(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(
        timezone.utc
    )


def make_bar(
    timestamp: str,
    *,
    close: str = "2.746",
) -> VersionedResearchBar:
    value = Decimal(close)

    return build_bar(
        dataset_version=NATIVE_FINAM_M5_V1,
        symbol="NGU6@RTSX",
        timeframe="M5",
        ts=ts(timestamp),
        open=value,
        high=value,
        low=value,
        close=value,
        volume=Decimal("1"),
        provider="FINAM_GRPC",
        provider_data_version="FINAM_NATIVE_M5_V1",
    )


def test_split_candidate_identical_prefix_and_new_suffix():
    persisted = [
        make_bar("2026-08-08T10:55:00+00:00"),
        make_bar("2026-08-08T11:00:00+00:00"),
    ]

    candidate = [
        make_bar("2026-08-08T11:00:00+00:00"),
        make_bar("2026-08-08T11:05:00+00:00"),
        make_bar("2026-08-08T11:10:00+00:00"),
    ]

    result = builder.classify_continuation(
        persisted,
        candidate,
    )

    assert result.overlap_identical == 1
    assert result.new_rows == 2
    assert [
        bar.ts for bar in result.suffix
    ] == [
        ts("2026-08-08T11:05:00+00:00"),
        ts("2026-08-08T11:10:00+00:00"),
    ]


def test_historical_conflict_fails_closed():
    persisted = [
        make_bar("2026-08-08T11:00:00+00:00"),
    ]

    candidate = [
        make_bar(
            "2026-08-08T11:00:00+00:00",
            close="2.747",
        ),
    ]

    with pytest.raises(
        RuntimeError,
        match="continuation_historical_conflict",
    ):
        builder.classify_continuation(
            persisted,
            candidate,
        )


def test_candidate_before_persisted_tail_must_be_known():
    persisted = [
        make_bar("2026-08-08T10:55:00+00:00"),
        make_bar("2026-08-08T11:00:00+00:00"),
    ]

    candidate = [
        make_bar("2026-08-08T10:50:00+00:00"),
    ]

    with pytest.raises(
        RuntimeError,
        match="continuation_unknown_historical_timestamp",
    ):
        builder.classify_continuation(
            persisted,
            candidate,
        )


def test_no_new_data_is_valid():
    persisted = [
        make_bar("2026-08-08T11:00:00+00:00"),
    ]

    candidate = [
        make_bar("2026-08-08T11:00:00+00:00"),
    ]

    result = builder.classify_continuation(
        persisted,
        candidate,
    )

    assert result.overlap_identical == 1
    assert result.new_rows == 0
    assert result.suffix == []


def test_prefix_fingerprint_must_remain_unchanged():
    prefix = [
        make_bar("2026-08-08T10:55:00+00:00"),
        make_bar("2026-08-08T11:00:00+00:00"),
    ]

    expected = builder.dataset_fingerprint(prefix)

    assert (
        builder.verify_prefix_fingerprint(
            prefix,
            expected,
        )
        == expected
    )


def test_prefix_fingerprint_change_fails_closed():
    prefix = [
        make_bar("2026-08-08T11:00:00+00:00"),
    ]

    with pytest.raises(
        RuntimeError,
        match="historical_prefix_fingerprint_mismatch",
    ):
        builder.verify_prefix_fingerprint(
            prefix,
            "not-the-real-fingerprint",
        )


def test_source_has_no_update_or_delete_mutation():
    source = SCRIPT.read_text()

    forbidden = (
        "DO UPDATE",
        "UPDATE analytics.research_market_bars_v1",
        "DELETE FROM analytics.research_market_bars_v1",
    )

    for value in forbidden:
        assert value not in source


def test_candidate_identity_contract_accepts_native_ngu6_m5():
    bars = [
        make_bar("2026-08-08T11:05:00+00:00"),
        make_bar("2026-08-08T11:10:00+00:00"),
    ]

    builder.validate_candidate_identity(bars)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("dataset_version", "OTHER_DATASET"),
        ("symbol", "OTHER@RTSX"),
        ("timeframe", "M1"),
        ("provider", "OTHER_PROVIDER"),
        ("provider_data_version", "OTHER_VERSION"),
    ],
)
def test_candidate_identity_mismatch_fails_closed(
    field,
    value,
):
    bar = make_bar(
        "2026-08-08T11:05:00+00:00"
    )

    kwargs = {
        "dataset_version": bar.dataset_version,
        "symbol": bar.symbol,
        "timeframe": bar.timeframe,
        "ts": bar.ts,
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "volume": bar.volume,
        "provider": bar.provider,
        "provider_data_version":
            bar.provider_data_version,
        "source_payload_hash":
            bar.source_payload_hash,
    }

    kwargs[field] = value

    bad = VersionedResearchBar(**kwargs)

    with pytest.raises(
        RuntimeError,
        match="continuation_identity_mismatch",
    ):
        builder.validate_candidate_identity([bad])


def test_candidate_ordering_must_be_strictly_increasing():
    bars = [
        make_bar("2026-08-08T11:10:00+00:00"),
        make_bar("2026-08-08T11:05:00+00:00"),
    ]

    with pytest.raises(
        RuntimeError,
        match="continuation_candidate_not_strictly_ordered",
    ):
        builder.validate_candidate_ordering(bars)


def test_candidate_ordering_accepts_empty_and_single():
    builder.validate_candidate_ordering([])

    builder.validate_candidate_ordering([
        make_bar("2026-08-08T11:05:00+00:00")
    ])


def test_write_mode_uses_atomic_append_surface():
    source = SCRIPT.read_text()

    assert "write_mode_not_implemented" not in source
    assert "persist_continuation" in source
    assert "ingest_many" in source
    assert "connection.commit()" in source


def test_write_surface_has_no_update_or_delete():
    source = SCRIPT.read_text()

    forbidden = (
        "DO UPDATE",
        "UPDATE analytics.research_market_bars_v1",
        "DELETE FROM analytics.research_market_bars_v1",
    )

    for value in forbidden:
        assert value not in source


def test_continuation_dry_run_returns_before_persistence():
    source = SCRIPT.read_text()

    main_source = source[
        source.index("def main() -> int:"):
    ]

    dry_run_guard = main_source.index(
        "if not args.write:"
    )
    dry_run_return = main_source.index(
        "return 0",
        dry_run_guard,
    )
    persist_call = main_source.index(
        "= persist_continuation("
    )

    assert dry_run_guard < dry_run_return
    assert dry_run_return < persist_call
    assert "persist_dataset" not in source


def test_overlap_start_precedes_persisted_tail():
    tail = ts("2026-08-08T11:00:00+00:00")

    start = builder.continuation_overlap_start(
        tail,
        overlap_days=3,
    )

    assert start == ts(
        "2026-08-05T11:00:00+00:00"
    )


def test_overlap_days_must_be_positive():
    tail = ts("2026-08-08T11:00:00+00:00")

    with pytest.raises(
        RuntimeError,
        match="overlap_days_must_be_positive",
    ):
        builder.continuation_overlap_start(
            tail,
            overlap_days=0,
        )


def test_base_prefix_anchor_accepts_extended_dataset():
    base = [
        make_bar("2026-08-08T10:55:00+00:00"),
        make_bar("2026-08-08T11:00:00+00:00"),
    ]
    extended = base + [
        make_bar("2026-08-08T11:10:00+00:00"),
        make_bar("2026-08-08T11:20:00+00:00"),
    ]

    expected = builder.dataset_fingerprint(base)

    builder.verify_base_prefix_anchor(
        extended,
        base_last=ts("2026-08-08T11:00:00+00:00"),
        base_count=2,
        base_fingerprint=expected,
        fingerprint_fn=builder.dataset_fingerprint,
    )


def test_base_prefix_anchor_detects_changed_history():
    base = [
        make_bar("2026-08-08T10:55:00+00:00"),
        make_bar("2026-08-08T11:00:00+00:00"),
    ]

    expected = builder.dataset_fingerprint(base)

    changed = [
        make_bar("2026-08-08T10:55:00+00:00"),
        make_bar(
            "2026-08-08T11:00:00+00:00",
            close="2.747",
        ),
        make_bar("2026-08-08T11:10:00+00:00"),
    ]

    with pytest.raises(
        RuntimeError,
        match="base_prefix_fingerprint_mismatch",
    ):
        builder.verify_base_prefix_anchor(
            changed,
            base_last=ts(
                "2026-08-08T11:00:00+00:00"
            ),
            base_count=2,
            base_fingerprint=expected,
            fingerprint_fn=builder.dataset_fingerprint,
        )


def test_base_prefix_anchor_detects_missing_base_row():
    base = [
        make_bar("2026-08-08T10:55:00+00:00"),
        make_bar("2026-08-08T11:00:00+00:00"),
    ]

    expected = builder.dataset_fingerprint(base)

    incomplete = [
        base[1],
        make_bar("2026-08-08T11:10:00+00:00"),
    ]

    with pytest.raises(
        RuntimeError,
        match="base_prefix_count_mismatch",
    ):
        builder.verify_base_prefix_anchor(
            incomplete,
            base_last=ts(
                "2026-08-08T11:00:00+00:00"
            ),
            base_count=2,
            base_fingerprint=expected,
            fingerprint_fn=builder.dataset_fingerprint,
        )

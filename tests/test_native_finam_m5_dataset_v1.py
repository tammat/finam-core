import importlib.util
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from finam_core.research.versioned_market_bars_v1 import (
    NATIVE_FINAM_M5_V1,
    build_bar,
)


SCRIPT = Path(
    "scripts/research/"
    "build_native_finam_m5_dataset_v1.py"
)

MODULE_NAME = "native_finam_m5_dataset_builder_test"

spec = importlib.util.spec_from_file_location(
    MODULE_NAME,
    SCRIPT,
)

assert spec is not None
assert spec.loader is not None

builder = importlib.util.module_from_spec(spec)
sys.modules[MODULE_NAME] = builder
spec.loader.exec_module(builder)


def make_bar(
    minute: int,
    *,
    close: str = "2.746",
):
    ts = datetime(
        2026, 8, 8, 10, minute,
        tzinfo=timezone.utc,
    )

    close_value = Decimal(close)

    return build_bar(
        dataset_version=NATIVE_FINAM_M5_V1,
        symbol="NGU6@RTSX",
        timeframe="M5",
        ts=ts,
        open=Decimal("2.746"),
        high=max(
            Decimal("2.747"),
            close_value,
        ),
        low=min(
            Decimal("2.745"),
            close_value,
        ),
        close=close_value,
        volume=Decimal("10"),
        provider=builder.PROVIDER,
        provider_data_version=(
            builder.PROVIDER_DATA_VERSION
        ),
    )


def test_identical_overlap_is_deduplicated():
    first = make_bar(0)
    overlap = make_bar(5)
    last = make_bar(10)

    merged = builder.merge_chunk_bars(
        [
            [first, overlap],
            [overlap, last],
        ]
    )

    assert merged == [
        first,
        overlap,
        last,
    ]


def test_conflicting_overlap_fails_closed():
    original = make_bar(5)
    conflicting = make_bar(
        5,
        close="2.700",
    )

    with pytest.raises(
        RuntimeError,
        match="native_finam_chunk_overlap_conflict",
    ):
        builder.merge_chunk_bars(
            [
                [original],
                [conflicting],
            ]
        )


def test_merge_result_is_sorted():
    bars = [
        make_bar(10),
        make_bar(0),
        make_bar(5),
    ]

    merged = builder.merge_chunk_bars(
        [bars]
    )

    assert [
        bar.ts.minute
        for bar in merged
    ] == [0, 5, 10]


def test_fingerprint_independent_of_chunk_partition():
    a = make_bar(0)
    b = make_bar(5)
    c = make_bar(10)

    seven_day_style = builder.merge_chunk_bars(
        [
            [a, b],
            [b, c],
        ]
    )

    fourteen_day_style = (
        builder.merge_chunk_bars(
            [
                [a, b, c],
            ]
        )
    )

    assert seven_day_style == fourteen_day_style

    assert (
        builder.dataset_fingerprint(
            seven_day_style
        )
        == builder.dataset_fingerprint(
            fourteen_day_style
        )
    )


def test_fingerprint_changes_when_payload_changes():
    original = [
        make_bar(0),
        make_bar(5),
    ]

    changed = [
        make_bar(0),
        make_bar(
            5,
            close="2.700",
        ),
    ]

    assert (
        builder.dataset_fingerprint(original)
        != builder.dataset_fingerprint(changed)
    )


def test_validate_rejects_duplicate_timestamp():
    bar = make_bar(0)

    with pytest.raises(
        RuntimeError,
        match="duplicate_timestamp",
    ):
        builder.validate_dataset(
            [bar, bar],
            start=datetime(
                2026, 8, 8, 0, 0,
                tzinfo=timezone.utc,
            ),
            end=datetime(
                2026, 8, 9, 0, 0,
                tzinfo=timezone.utc,
            ),
        )


def test_write_mode_is_not_implemented_in_source():
    source = SCRIPT.read_text()

    assert "write_mode_not_implemented" in source

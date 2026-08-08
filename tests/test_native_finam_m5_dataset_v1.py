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


def test_write_mode_uses_controlled_persistence_path():
    source = SCRIPT.read_text()

    assert "write_mode_not_implemented" not in source
    assert "persist_dataset(bars)" in source
    assert "post_write_fingerprint_changed" in source
    assert "RESEARCH_USE_ALLOWED=0" in source


def test_verify_persisted_dataset_accepts_identical():
    bars = [
        make_bar(0),
        make_bar(5),
        make_bar(10),
    ]

    fingerprint = builder.verify_persisted_dataset(
        bars,
        bars,
    )

    assert fingerprint == builder.dataset_fingerprint(
        bars
    )


def test_verify_persisted_dataset_rejects_count_mismatch():
    expected = [
        make_bar(0),
        make_bar(5),
    ]

    persisted = [
        make_bar(0),
    ]

    with pytest.raises(
        RuntimeError,
        match="persisted_dataset_count_mismatch",
    ):
        builder.verify_persisted_dataset(
            persisted,
            expected,
        )


def test_verify_persisted_dataset_rejects_fingerprint_mismatch():
    expected = [
        make_bar(0),
        make_bar(5),
    ]

    persisted = [
        make_bar(0),
        make_bar(
            5,
            close="2.700",
        ),
    ]

    with pytest.raises(
        RuntimeError,
        match="persisted_dataset_fingerprint_mismatch",
    ):
        builder.verify_persisted_dataset(
            persisted,
            expected,
        )


def test_persist_dataset_rejects_empty_before_db(monkeypatch):
    called = False

    def forbidden_connect(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("database_connect_not_allowed")

    monkeypatch.setattr(
        builder.psycopg2,
        "connect",
        forbidden_connect,
    )

    with pytest.raises(
        RuntimeError,
        match="cannot_persist_empty_dataset",
    ):
        builder.persist_dataset([])

    assert called is False


def test_persist_dataset_rejects_mixed_identity_before_db(
    monkeypatch,
):
    first = make_bar(0)

    second = build_bar(
        dataset_version=NATIVE_FINAM_M5_V1,
        symbol="OTHER@TEST",
        timeframe="M5",
        ts=datetime(
            2026, 8, 8, 10, 5,
            tzinfo=timezone.utc,
        ),
        open=Decimal("2.746"),
        high=Decimal("2.747"),
        low=Decimal("2.745"),
        close=Decimal("2.746"),
        volume=Decimal("10"),
        provider=builder.PROVIDER,
        provider_data_version=(
            builder.PROVIDER_DATA_VERSION
        ),
    )

    called = False

    def forbidden_connect(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("database_connect_not_allowed")

    monkeypatch.setattr(
        builder.psycopg2,
        "connect",
        forbidden_connect,
    )

    with pytest.raises(
        RuntimeError,
        match="mixed_dataset_identity_not_allowed",
    ):
        builder.persist_dataset(
            [first, second]
        )

    assert called is False


def test_main_dry_run_never_calls_persist_dataset(
    monkeypatch,
):
    bars = [
        make_bar(0),
        make_bar(5),
    ]

    class FakeClient:
        def close(self):
            pass

    monkeypatch.setattr(
        builder,
        "FinamBarsClient",
        FakeClient,
    )

    monkeypatch.setattr(
        builder,
        "fetch_chunked_bars",
        lambda *args, **kwargs: (bars, 1),
    )

    persist_calls = []

    def forbidden_persist(value):
        persist_calls.append(value)
        raise AssertionError(
            "persist_dataset_called_in_dry_run"
        )

    monkeypatch.setattr(
        builder,
        "persist_dataset",
        forbidden_persist,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--start",
            "2026-08-08T10:00:00+00:00",
            "--end",
            "2026-08-08T11:00:00+00:00",
        ],
    )

    assert builder.main() == 0
    assert persist_calls == []


def test_main_write_calls_persist_exactly_once(
    monkeypatch,
):
    bars = [
        make_bar(0),
        make_bar(5),
    ]

    class FakeClient:
        def close(self):
            pass

    monkeypatch.setattr(
        builder,
        "FinamBarsClient",
        FakeClient,
    )

    monkeypatch.setattr(
        builder,
        "fetch_chunked_bars",
        lambda *args, **kwargs: (bars, 1),
    )

    calls = []

    class Result:
        rows_seen = 2
        rows_inserted = 2
        rows_identical = 0

    expected_fingerprint = (
        builder.dataset_fingerprint(bars)
    )

    def fake_persist(value):
        calls.append(value)
        return Result(), expected_fingerprint

    monkeypatch.setattr(
        builder,
        "persist_dataset",
        fake_persist,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--start",
            "2026-08-08T10:00:00+00:00",
            "--end",
            "2026-08-08T11:00:00+00:00",
            "--write",
        ],
    )

    assert builder.main() == 0
    assert calls == [bars]


def test_main_write_rejects_post_write_fingerprint_change(
    monkeypatch,
):
    bars = [
        make_bar(0),
        make_bar(5),
    ]

    class FakeClient:
        def close(self):
            pass

    monkeypatch.setattr(
        builder,
        "FinamBarsClient",
        FakeClient,
    )

    monkeypatch.setattr(
        builder,
        "fetch_chunked_bars",
        lambda *args, **kwargs: (bars, 1),
    )

    class Result:
        rows_seen = 2
        rows_inserted = 2
        rows_identical = 0

    monkeypatch.setattr(
        builder,
        "persist_dataset",
        lambda value: (
            Result(),
            "0" * 64,
        ),
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--start",
            "2026-08-08T10:00:00+00:00",
            "--end",
            "2026-08-08T11:00:00+00:00",
            "--write",
        ],
    )

    with pytest.raises(
        RuntimeError,
        match="post_write_fingerprint_changed",
    ):
        builder.main()

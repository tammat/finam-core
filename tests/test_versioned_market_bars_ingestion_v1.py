from datetime import datetime, timezone
from decimal import Decimal

import pytest

from finam_core.research.versioned_market_bars_ingestion_v1 import (
    ingest_many,
    ingest_one,
)
from finam_core.research.versioned_market_bars_v1 import (
    NATIVE_FINAM_M5_V1,
    VersionedMarketBarsContractError,
    build_bar,
)


TS = datetime(
    2026, 8, 8, 10, 25,
    tzinfo=timezone.utc,
)


def make_bar(**overrides):
    values = {
        "dataset_version": NATIVE_FINAM_M5_V1,
        "symbol": "NGU6@RTSX",
        "timeframe": "M5",
        "ts": TS,
        "open": Decimal("2.746"),
        "high": Decimal("2.747"),
        "low": Decimal("2.745"),
        "close": Decimal("2.746"),
        "volume": Decimal("10"),
        "provider": "FINAM_GRPC",
        "provider_data_version": "FINAM_NATIVE_M5_V1",
    }
    values.update(overrides)
    return build_bar(**values)


def existing_from_bar(bar):
    return {
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "volume": bar.volume,
        "provider": bar.provider,
        "provider_data_version": bar.provider_data_version,
        "source_payload_hash": bar.source_payload_hash,
    }


class FakeCursor:
    def __init__(
        self,
        *,
        fetches=None,
        insert_rowcounts=None,
    ):
        self.fetches = list(fetches or [])
        self.insert_rowcounts = list(
            insert_rowcounts or []
        )
        self.executions = []
        self.rowcount = -1

    def execute(self, query, values=None):
        text = str(query)
        self.executions.append(
            (text, values)
        )

        if "INSERT INTO" in text.upper():
            self.rowcount = (
                self.insert_rowcounts.pop(0)
                if self.insert_rowcounts
                else 1
            )
        else:
            self.rowcount = -1

    def fetchone(self):
        if not self.fetches:
            return None
        return self.fetches.pop(0)


def test_new_bar_is_inserted():
    bar = make_bar()

    cursor = FakeCursor(
        fetches=[None],
        insert_rowcounts=[1],
    )

    outcome = ingest_one(
        cursor,
        bar,
    )

    assert outcome == "INSERTED"
    assert len(cursor.executions) == 2
    assert "SELECT" in cursor.executions[0][0].upper()
    assert "INSERT INTO" in cursor.executions[1][0].upper()


def test_existing_identical_is_noop_without_insert():
    bar = make_bar()

    cursor = FakeCursor(
        fetches=[
            existing_from_bar(bar),
        ],
    )

    outcome = ingest_one(
        cursor,
        bar,
    )

    assert outcome == "IDENTICAL"
    assert len(cursor.executions) == 1


def test_existing_different_fails_closed():
    bar = make_bar()

    existing = existing_from_bar(bar)
    existing["close"] = Decimal("2.700")

    cursor = FakeCursor(
        fetches=[existing],
    )

    with pytest.raises(
        VersionedMarketBarsContractError,
        match="immutable_dataset_conflict",
    ):
        ingest_one(
            cursor,
            bar,
        )

    assert len(cursor.executions) == 1


def test_concurrent_identical_insert_is_idempotent():
    bar = make_bar()

    cursor = FakeCursor(
        fetches=[
            None,
            existing_from_bar(bar),
        ],
        insert_rowcounts=[0],
    )

    outcome = ingest_one(
        cursor,
        bar,
    )

    assert outcome == "IDENTICAL"
    assert len(cursor.executions) == 3


def test_concurrent_different_insert_fails_closed():
    bar = make_bar()

    conflicting = existing_from_bar(bar)
    conflicting["provider"] = "OTHER_PROVIDER"

    cursor = FakeCursor(
        fetches=[
            None,
            conflicting,
        ],
        insert_rowcounts=[0],
    )

    with pytest.raises(
        VersionedMarketBarsContractError,
        match="immutable_dataset_conflict",
    ):
        ingest_one(
            cursor,
            bar,
        )

    assert len(cursor.executions) == 3


def test_conflict_without_existing_row_fails_closed():
    bar = make_bar()

    cursor = FakeCursor(
        fetches=[
            None,
            None,
        ],
        insert_rowcounts=[0],
    )

    with pytest.raises(
        RuntimeError,
        match="conflict_without_existing_row",
    ):
        ingest_one(
            cursor,
            bar,
        )


def test_duplicate_identity_inside_batch_fails_closed():
    bar = make_bar()

    cursor = FakeCursor(
        fetches=[None],
        insert_rowcounts=[1],
    )

    with pytest.raises(
        RuntimeError,
        match="duplicate_bar_identity_in_ingestion_payload",
    ):
        ingest_many(
            cursor,
            [bar, bar],
        )


def test_ingest_many_counts_inserted_and_identical():
    first = make_bar()

    second = make_bar(
        ts=datetime(
            2026, 8, 8, 10, 30,
            tzinfo=timezone.utc,
        )
    )

    cursor = FakeCursor(
        fetches=[
            None,
            existing_from_bar(second),
        ],
        insert_rowcounts=[1],
    )

    result = ingest_many(
        cursor,
        [first, second],
    )

    assert result.rows_seen == 2
    assert result.rows_inserted == 1
    assert result.rows_identical == 1


def test_ingestor_contains_no_update_or_delete():
    from pathlib import Path

    source = Path(
        "src/finam_core/research/"
        "versioned_market_bars_ingestion_v1.py"
    ).read_text().lower()

    assert "do update" not in source
    assert (
        "update analytics.research_market_bars"
        not in source
    )
    assert (
        "delete from analytics.research_market_bars"
        not in source
    )

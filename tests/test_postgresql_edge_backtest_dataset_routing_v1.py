from dataclasses import replace
from datetime import datetime, timezone

import pytest

from finam_core.research.postgresql_edge_backtest_adapter_v1 import (
    AdapterContractError,
    ResearchTask,
    load_bars,
)


def make_task(
    dataset_version: str = "default",
) -> ResearchTask:
    return ResearchTask(
        id=1,
        run_uuid=__import__("uuid").uuid4(),
        research_batch_id="TEST",
        research_code="TEST",
        strategy_code="MEAN_REVERSION_ZSCORE_V1",
        strategy_version="V1",
        symbol="NGU6@RTSX",
        timeframe="M5",
        parameter_hash="test",
        parameter_json={},
        dataset_version=dataset_version,
        runner_version="TEST",
        source_version="TEST",
    )


class Cursor:
    def __init__(self):
        self.executions = []
        self.values = None
        self.query = None
        self._fetch_mode = "columns"

    def execute(self, query, values=None):
        self.query = query
        self.values = values
        self.executions.append((query, values))

        text = repr(query)

        if "information_schema.columns" in text:
            self._fetch_mode = "columns"
        else:
            self._fetch_mode = "bars"

    def fetchall(self):
        if self._fetch_mode == "columns":
            return [
                {"column_name": "ts"},
                {"column_name": "symbol"},
                {"column_name": "timeframe"},
                {"column_name": "open"},
                {"column_name": "high"},
                {"column_name": "low"},
                {"column_name": "close"},
                {"column_name": "volume"},
                {"column_name": "dataset_version"},
            ]

        return []


def query_repr(cursor: Cursor) -> str:
    return repr(cursor.query)


def test_default_dataset_preserves_legacy_route():
    cursor = Cursor()

    load_bars(
        cursor,
        make_task("default"),
        {
            "bar_schema": "public",
            "bar_table": "market_bars",
            "bar_limit": 20000,
        },
    )

    text = query_repr(cursor)

    assert "Identifier('public')" in text
    assert "Identifier('market_bars')" in text

    assert cursor.values == [
        "NGU6@RTSX",
        "M5",
        20000,
    ]


def test_native_dataset_routes_to_versioned_storage():
    cursor = Cursor()

    load_bars(
        cursor,
        make_task("NATIVE_FINAM_M5_V1"),
        {
            "bar_limit": 20000,
        },
    )

    text = query_repr(cursor)

    assert "Identifier('analytics')" in text
    assert (
        "Identifier('research_market_bars_v1')"
        in text
    )
    assert "Identifier('dataset_version')" in text

    assert cursor.values == [
        "NGU6@RTSX",
        "M5",
        "NATIVE_FINAM_M5_V1",
        20000,
    ]


def test_native_dataset_cannot_override_storage_route():
    cursor = Cursor()

    load_bars(
        cursor,
        make_task("NATIVE_FINAM_M5_V1"),
        {
            "bar_schema": "public",
            "bar_table": "market_bars",
            "bar_limit": 20000,
        },
    )

    text = query_repr(cursor)

    assert "Identifier('analytics')" in text
    assert (
        "Identifier('research_market_bars_v1')"
        in text
    )

    assert "Identifier('public')" not in text


def test_native_temporal_bounds_preserve_bind_order():
    cursor = Cursor()

    start = datetime(
        2026, 7, 1,
        tzinfo=timezone.utc,
    )
    end = datetime(
        2026, 8, 1,
        tzinfo=timezone.utc,
    )

    load_bars(
        cursor,
        make_task("NATIVE_FINAM_M5_V1"),
        {
            "bar_start_ts": start,
            "bar_end_ts": end,
            "bar_limit": 20000,
        },
    )

    assert cursor.values == [
        "NGU6@RTSX",
        "M5",
        "NATIVE_FINAM_M5_V1",
        start,
        end,
        20000,
    ]


def test_unknown_dataset_version_fails_closed():
    cursor = Cursor()

    with pytest.raises(
        AdapterContractError,
        match="unsupported_dataset_version",
    ):
        load_bars(
            cursor,
            make_task("UNKNOWN_DATASET_V99"),
            {
                "bar_limit": 20000,
            },
        )

    assert cursor.executions == []

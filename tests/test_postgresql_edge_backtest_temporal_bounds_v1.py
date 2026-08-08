from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from finam_core.research.postgresql_edge_backtest_adapter_v1 import (
    ResearchTask,
    load_bars,
)


class FakeCursor:
    def __init__(self):
        self.query = None
        self.values = None

    def execute(self, query, values):
        self.query = query
        self.values = list(values)

    def fetchall(self):
        return []


def make_task():
    return ResearchTask(
        id=1,
        run_uuid=uuid4(),
        research_batch_id="TEST_TEMPORAL_BOUNDS",
        research_code="TEST_TEMPORAL_BOUNDS",
        strategy_code="MEAN_REVERSION_ZSCORE_V1",
        strategy_version="v1",
        symbol="NGU6@RTSX",
        timeframe="M5",
        parameter_hash="test",
        parameter_json={},
        dataset_version="default",
        runner_version="test",
        source_version="test",
    )


BAR_CONTRACT = {
    "timestamp": "ts",
    "symbol": "symbol",
    "timeframe": "timeframe",
    "volume": "volume",
}


def run_load(parameters):
    cursor = FakeCursor()

    with patch(
        "finam_core.research."
        "postgresql_edge_backtest_adapter_v1."
        "discover_bar_contract",
        return_value=BAR_CONTRACT,
    ):
        load_bars(
            cursor,
            make_task(),
            parameters,
        )

    return cursor


def test_load_bars_legacy_bind_values_unchanged():
    cursor = run_load(
        {
            "bar_schema": "public",
            "bar_table": "market_bars",
            "bar_limit": 20000,
        }
    )

    assert cursor.values == [
        "NGU6@RTSX",
        "M5",
        20000,
    ]


def test_load_bars_start_bound_is_parameterized():
    start = datetime(
        2026, 5, 24, 7, 20,
        tzinfo=timezone.utc,
    )

    cursor = run_load(
        {
            "bar_limit": 20000,
            "bar_start_ts": start,
        }
    )

    assert cursor.values == [
        "NGU6@RTSX",
        "M5",
        start,
        20000,
    ]


def test_load_bars_end_bound_is_parameterized():
    end = datetime(
        2026, 6, 29, 13, 15,
        tzinfo=timezone.utc,
    )

    cursor = run_load(
        {
            "bar_limit": 20000,
            "bar_end_ts": end,
        }
    )

    assert cursor.values == [
        "NGU6@RTSX",
        "M5",
        end,
        20000,
    ]


def test_load_bars_both_bounds_preserve_bind_order():
    start = datetime(
        2026, 5, 24, 7, 20,
        tzinfo=timezone.utc,
    )
    end = datetime(
        2026, 6, 29, 13, 15,
        tzinfo=timezone.utc,
    )

    cursor = run_load(
        {
            "bar_limit": 20000,
            "bar_start_ts": start,
            "bar_end_ts": end,
        }
    )

    assert cursor.values == [
        "NGU6@RTSX",
        "M5",
        start,
        end,
        20000,
    ]

    query_repr = repr(cursor.query)

    assert "Identifier('ts'), SQL(' >= %s')" in query_repr
    assert "Identifier('ts'), SQL(' <= %s')" in query_repr

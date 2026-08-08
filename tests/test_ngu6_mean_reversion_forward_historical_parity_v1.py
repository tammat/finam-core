from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.ngu6_mean_reversion_forward_observer_v1 import (
    ContractSpecSnapshot,
    build_forward_observations,
)
from finam_core.research.postgresql_edge_backtest_adapter_v1 import Bar


RUN_UUID = "149e775b-fc6e-4408-a2ee-98ae5db1bdf8"

TEST_BOUNDARY = datetime(
    2026, 7, 16, 7, 0,
    tzinfo=timezone.utc,
)

C_END = datetime(
    2026, 8, 5, 14, 20,
    tzinfo=timezone.utc,
)


def test_window_c_lb10_historical_trade_semantics_parity():
    with psycopg2.connect(build_psycopg_url()) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT ts, open, high, low, close, volume
                FROM public.market_bars
                WHERE symbol = 'NGU6@RTSX'
                  AND timeframe = 'M5'
                  AND ts <= %s
                ORDER BY ts
                """,
                (C_END,),
            )

            bars = [
                Bar(
                    ts=r["ts"],
                    open=Decimal(str(r["open"])),
                    high=Decimal(str(r["high"])),
                    low=Decimal(str(r["low"])),
                    close=Decimal(str(r["close"])),
                    volume=Decimal(str(r["volume"] or 0)),
                )
                for r in cur.fetchall()
            ]

            cur.execute(
                """
                SELECT
                    trade_no,
                    side,
                    entry_ts,
                    exit_ts,
                    entry_price,
                    exit_price
                FROM analytics.research_trade_v1
                WHERE run_uuid = %s
                ORDER BY trade_no
                """,
                (RUN_UUID,),
            )

            historical = cur.fetchall()

    specs = {
        bar.ts: ContractSpecSnapshot(
            contract_spec_id=1,
            valid_from=TEST_BOUNDARY,
            valid_to=None,
            tick_size=Decimal("0.001"),
            tick_value=Decimal("8"),
            contract_multiplier=Decimal("8000"),
            source_version="PARITY_TEST",
        )
        for bar in bars
        if bar.ts > TEST_BOUNDARY
    }

    with patch(
        "finam_core.research."
        "ngu6_mean_reversion_forward_observer_v1."
        "FORWARD_BOUNDARY",
        TEST_BOUNDARY,
    ):
        observed = build_forward_observations(
            bars,
            specs,
        )

    closed = [
        observation
        for observation in observed
        if observation.status == "CLOSED"
    ]

    assert len(historical) == 21
    assert len(closed) == 21

    for expected, actual in zip(
        historical,
        closed,
        strict=True,
    ):
        assert actual.side == expected["side"]
        assert actual.signal_ts == expected["entry_ts"]
        assert actual.exit_ts == expected["exit_ts"]

        assert actual.entry_price == Decimal(
            str(expected["entry_price"])
        )

        assert actual.exit_price == Decimal(
            str(expected["exit_price"])
        )

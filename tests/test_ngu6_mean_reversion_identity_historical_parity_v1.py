from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import (
    build_psycopg_url,
)
from finam_core.research.ngu6_mean_reversion_forward_observer_v1 import (
    ContractSpecSnapshot,
    build_forward_observations,
)
from finam_core.research.ngu6_mean_reversion_identity_observer_v1 import (
    build_identity_observations,
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


def _load_bars() -> list[Bar]:
    with psycopg2.connect(build_psycopg_url()) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT
                    ts,
                    open,
                    high,
                    low,
                    close,
                    volume
                FROM public.market_bars
                WHERE symbol = 'NGU6@RTSX'
                  AND timeframe = 'M5'
                  AND ts <= %s
                ORDER BY ts
                """,
                (C_END,),
            )

            return [
                Bar(
                    ts=row["ts"],
                    open=Decimal(str(row["open"])),
                    high=Decimal(str(row["high"])),
                    low=Decimal(str(row["low"])),
                    close=Decimal(str(row["close"])),
                    volume=Decimal(
                        str(row["volume"] or 0)
                    ),
                )
                for row in cur.fetchall()
            ]


def _specs(
    bars: list[Bar],
) -> dict[datetime, ContractSpecSnapshot]:
    return {
        bar.ts: ContractSpecSnapshot(
            contract_spec_id=1,
            valid_from=TEST_BOUNDARY,
            valid_to=None,
            tick_size=Decimal("0.001"),
            tick_value=Decimal("8"),
            contract_multiplier=Decimal("8000"),
            source_version="IDENTITY_PARITY_TEST",
        )
        for bar in bars
        if bar.ts > TEST_BOUNDARY
    }


def test_identity_only_builder_matches_forward_trade_identity():
    bars = _load_bars()
    specs = _specs(bars)

    with patch(
        "finam_core.research."
        "ngu6_mean_reversion_forward_observer_v1."
        "FORWARD_BOUNDARY",
        TEST_BOUNDARY,
    ):
        forward = build_forward_observations(
            bars,
            specs,
        )

    identity = build_identity_observations(
        bars,
        specs,
        boundary=TEST_BOUNDARY,
    )

    assert len(identity) == len(forward)

    for expected, actual in zip(
        forward,
        identity,
        strict=True,
    ):
        assert actual.candidate_code == (
            expected.candidate_code
        )
        assert actual.signal_ts == expected.signal_ts
        assert actual.side == expected.side
        assert actual.exit_ts == expected.exit_ts
        assert actual.contract_spec_id == (
            expected.contract_spec.contract_spec_id
        )
        assert actual.status == expected.status


def test_identity_only_builder_has_no_monetary_fields():
    fields = {
        field.name
        for field in (
            __import__(
                "dataclasses"
            ).fields(
                __import__(
                    "finam_core.research."
                    "ngu6_mean_reversion_identity_observer_v1",
                    fromlist=["IdentityObservation"],
                ).IdentityObservation
            )
        )
    }

    forbidden = {
        "market_entry_price",
        "market_exit_price",
        "entry_price",
        "exit_price",
        "gross_pnl",
        "market_pnl",
        "commission",
        "slippage",
        "net_pnl",
    }

    assert fields.isdisjoint(forbidden)

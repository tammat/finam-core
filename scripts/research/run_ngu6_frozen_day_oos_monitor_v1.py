from __future__ import annotations

import importlib.util
import subprocess
import sys
from datetime import datetime, time, timezone
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.ngu6_mean_reversion_forward_observer_v1 import (
    ContractSpecSnapshot,
)
from finam_core.research.ngu6_mean_reversion_identity_observer_v1 import (
    build_identity_observations,
)
from finam_core.research.postgresql_edge_backtest_adapter_v1 import Bar


ROOT = Path("/opt/finam-core")

CONTINUATION_SCRIPT = (
    ROOT
    / "scripts/research/continue_native_finam_m5_dataset_v1.py"
)

OOS3_BOUNDARY = datetime(
    2026, 8, 8, 12, 45,
    tzinfo=timezone.utc,
)

DAY_START = time(8, 0)
DAY_END = time(15, 59, 59)

SYMBOL = "NGU6@RTSX"
TIMEFRAME = "M5"


class MonitorContractError(RuntimeError):
    pass


def run_continuation() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(CONTINUATION_SCRIPT),
            "--write",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    print("=== CONTINUATION ===")

    if result.stdout:
        print(result.stdout.rstrip())

    if result.returncode != 0:
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr)

        raise MonitorContractError(
            f"continuation_failed:{result.returncode}"
        )


def load_bars() -> list[Bar]:
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
                WHERE symbol = %s
                  AND timeframe = %s
                ORDER BY ts
                """,
                (SYMBOL, TIMEFRAME),
            )

            rows = cur.fetchall()

    if not rows:
        raise MonitorContractError(
            "native_m5_dataset_empty"
        )

    return [
        Bar(
            ts=row["ts"],
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"] or 0,
        )
        for row in rows
    ]


def load_contract_specs(
    bars: list[Bar],
) -> dict[datetime, ContractSpecSnapshot]:
    timestamps = [
        bar.ts
        for bar in bars
        if bar.ts > OOS3_BOUNDARY
    ]

    if not timestamps:
        return {}

    with psycopg2.connect(build_psycopg_url()) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT
                    id,
                    valid_from,
                    valid_to,
                    tick_size,
                    tick_value,
                    contract_multiplier,
                    source_version
                FROM analytics.instrument_contract_spec_v1
                WHERE symbol = %s
                ORDER BY valid_from
                """,
                (SYMBOL,),
            )

            specs = cur.fetchall()

    if not specs:
        raise MonitorContractError(
            "contract_spec_inventory_empty"
        )

    resolved: dict[datetime, ContractSpecSnapshot] = {}

    for ts in timestamps:
        matches = [
            row
            for row in specs
            if row["valid_from"] <= ts
            and (
                row["valid_to"] is None
                or ts < row["valid_to"]
            )
        ]

        if len(matches) != 1:
            raise MonitorContractError(
                "contract_spec_resolution_failed:"
                f"{ts.isoformat()}:matches={len(matches)}"
            )

        row = matches[0]

        resolved[ts] = ContractSpecSnapshot(
            contract_spec_id=row["id"],
            valid_from=row["valid_from"],
            valid_to=row["valid_to"],
            tick_size=row["tick_size"],
            tick_value=row["tick_value"],
            contract_multiplier=row["contract_multiplier"],
            source_version=row["source_version"],
        )

    return resolved


def is_day_trade(
    entry_ts: datetime,
    exit_ts: datetime,
) -> bool:
    if (
        entry_ts.tzinfo is None
        or exit_ts.tzinfo is None
    ):
        raise MonitorContractError(
            "naive_timestamp_detected"
        )

    entry_utc = entry_ts.astimezone(timezone.utc)
    exit_utc = exit_ts.astimezone(timezone.utc)

    if entry_utc.date() != exit_utc.date():
        return False

    return (
        DAY_START <= entry_utc.time() <= DAY_END
        and DAY_START <= exit_utc.time() <= DAY_END
    )


def main() -> int:
    print("MONITOR_VERSION=NGU6_FROZEN_DAY_OOS_MONITOR_V1")
    print(
        "OOS3_BOUNDARY="
        + OOS3_BOUNDARY.isoformat()
    )
    print("PNL_REVEALED=0")
    print("PARAMETER_SEARCH=NO")
    print("STRATEGY_CHANGED=0")

    run_continuation()

    bars = load_bars()

    print(f"DATASET_ROWS={len(bars)}")
    print(
        "DATASET_LAST="
        + bars[-1].ts.isoformat()
    )

    specs = load_contract_specs(bars)

    observations = build_identity_observations(
        bars,
        specs,
        boundary=OOS3_BOUNDARY,
    )

    new_closed = [
        observation
        for observation in observations
        if observation.status == "CLOSED"
        and observation.signal_ts > OOS3_BOUNDARY
        and observation.exit_ts is not None
        and is_day_trade(
            observation.signal_ts,
            observation.exit_ts,
        )
    ]

    print(
        "NEW_COMPLETED_DAY_TRADES="
        f"{len(new_closed)}"
    )

    if not new_closed:
        print("INVENTORY_FROZEN=0")
        print("PNL_REVEALED=0")
        print(
            "VERDICT="
            "NO_NEW_FROZEN_DAY_TRADES"
        )
        return 0

    print("INVENTORY_FROZEN=0")
    print("PNL_REVEALED=0")

    for index, observation in enumerate(
        new_closed,
        start=1,
    ):
        print(
            "TRADE_IDENTITY="
            f"{index}|"
            f"{observation.signal_ts.isoformat()}|"
            f"{observation.side}|"
            f"{observation.exit_ts.isoformat()}|"
            f"{observation.contract_spec_id}"
        )

    print(
        "VERDICT="
        "NEW_FROZEN_DAY_INVENTORY_READY"
    )

    return 2


if __name__ == "__main__":
    raise SystemExit(main())

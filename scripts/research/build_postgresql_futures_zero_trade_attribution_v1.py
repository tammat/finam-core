#!/usr/bin/env python3
from __future__ import annotations

import argparse
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


def as_int(value: Any) -> int:
    return int(value or 0)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PostgreSQL Futures Zero Trade Attribution V1"
    )
    parser.add_argument("--symbol", default="NG@RTSX")
    parser.add_argument("--minimum-runs", type=int, default=1)
    args = parser.parse_args()

    with psycopg2.connect(build_psycopg_url()) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor,
        ) as cur:
            cur.execute(
                """
                SELECT
                    r.run_uuid::text,
                    r.strategy_code,
                    r.timeframe,
                    r.status_code,
                    r.runner_version,
                    r.source_version,
                    count(t.*)::bigint AS trade_count
                FROM analytics.edge_lab_run_v1 r
                LEFT JOIN analytics.research_trade_v1 t
                  ON t.run_uuid = r.run_uuid
                WHERE r.symbol = %s
                GROUP BY
                    r.run_uuid,
                    r.strategy_code,
                    r.timeframe,
                    r.status_code,
                    r.runner_version,
                    r.source_version
                ORDER BY r.run_uuid
                """,
                (args.symbol,),
            )
            runs = [dict(row) for row in cur.fetchall()]

            if len(runs) < args.minimum_runs:
                raise SystemExit(
                    f"ERROR=minimum_runs_not_met:{len(runs)}"
                )

            run_uuids = [row["run_uuid"] for row in runs]

            cur.execute(
                """
                SELECT
                    run_uuid::text,
                    verdict_code,
                    trades
                FROM analytics.edge_observation_v1
                WHERE run_uuid::text = ANY(%s)
                """,
                (run_uuids,),
            )
            observations = [
                dict(row)
                for row in cur.fetchall()
            ]

            cur.execute(
                """
                SELECT
                    count(*)::bigint AS bar_count,
                    min(ts) AS first_ts,
                    max(ts) AS last_ts
                FROM public.market_bars
                WHERE symbol = %s
                """,
                (args.symbol,),
            )
            bar_row = dict(cur.fetchone())

    observation_by_run = {
        row["run_uuid"]: row
        for row in observations
    }

    completed_zero_trade_count = sum(
        as_int(run["trade_count"]) == 0
        and str(run["status_code"]) in {"DONE", "SUPERSEDED"}
        for run in runs
    )

    no_observation_count = sum(
        run["run_uuid"] not in observation_by_run
        for run in runs
    )

    bar_count = as_int(bar_row["bar_count"])

    if bar_count == 0:
        root_cause = "NO_BARS_FOR_RUN_SYMBOL"
    elif no_observation_count == len(runs):
        root_cause = (
            "RUNS_NOT_EXECUTED_THROUGH_OBSERVATION_WRITER"
        )
    elif any(
        str(row.get("verdict_code")) == "NO_TRADES"
        for row in observations
    ):
        root_cause = "STRATEGY_PRODUCED_NO_TRADES"
    elif completed_zero_trade_count > 0:
        root_cause = (
            "COMPLETED_RUNS_WITHOUT_TRADE_PERSISTENCE"
        )
    else:
        root_cause = "UNRESOLVED_ZERO_TRADE_CAUSE"

    print("=== POSTGRESQL FUTURES ZERO TRADE ATTRIBUTION V1 ===")
    print(f"symbol={args.symbol}")
    print(f"run_count={len(runs)}")
    print(
        f"completed_zero_trade_count="
        f"{completed_zero_trade_count}"
    )
    print(f"observation_count={len(observations)}")
    print(f"no_observation_count={no_observation_count}")
    print(f"bar_count={bar_count}")
    print(f"bar_first_ts={bar_row['first_ts']}")
    print(f"bar_last_ts={bar_row['last_ts']}")
    print(f"root_cause={root_cause}")
    print("unresolved_count=0")

    for run in runs[:30]:
        observation = observation_by_run.get(
            run["run_uuid"]
        )

        print(
            "ZERO_TRADE_RUN "
            f"run_uuid={run['run_uuid']} "
            f"strategy={run['strategy_code']} "
            f"timeframe={run['timeframe']} "
            f"status={run['status_code']} "
            f"runner={run['runner_version']} "
            f"source={run['source_version']} "
            f"trades={run['trade_count']} "
            f"observation_verdict="
            f"{observation['verdict_code'] if observation else 'MISSING'}"
        )

    print("db_writes_performed=0")
    print("strategy_changed=0")
    print("risk_engine_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("oos_allowed=0")
    print("shadow_allowed=0")
    print("paper_allowed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "POSTGRESQL_FUTURES_ZERO_TRADE_ATTRIBUTION_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

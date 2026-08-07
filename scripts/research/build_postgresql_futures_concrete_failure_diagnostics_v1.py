#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "PostgreSQL Futures Concrete Contract "
            "Failure Diagnostics V1"
        )
    )
    parser.add_argument("--batch-id", required=True)
    args = parser.parse_args()

    with psycopg2.connect(build_psycopg_url()) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor,
        ) as cursor:
            cursor.execute(
                """
                SELECT
                    r.id,
                    r.run_uuid::text,
                    r.research_batch_id,
                    r.research_code,
                    r.strategy_code,
                    r.strategy_version,
                    r.symbol,
                    r.timeframe,
                    r.status_code,
                    r.parameter_hash,
                    r.parameter_json,
                    r.dataset_version,
                    r.runner_version,
                    r.source_version,
                    r.created_at,
                    r.started_at,
                    r.finished_at
                FROM analytics.edge_lab_run_v1 r
                WHERE r.research_batch_id = %s
                ORDER BY r.created_at, r.id
                """,
                (args.batch_id,),
            )
            runs = [dict(row) for row in cursor.fetchall()]

            if not runs:
                raise SystemExit(
                    f"ERROR=batch_runs_missing:{args.batch_id}"
                )

            run_uuids = [
                row["run_uuid"]
                for row in runs
            ]

            cursor.execute(
                """
                SELECT
                    run_uuid::text,
                    count(*)::bigint AS trade_count,
                    sum(gross_pnl)::numeric AS gross_pnl,
                    sum(commission)::numeric AS commission,
                    sum(slippage)::numeric AS slippage,
                    sum(net_pnl)::numeric AS net_pnl
                FROM analytics.research_trade_v1
                WHERE run_uuid::text = ANY(%s)
                GROUP BY run_uuid
                """,
                (run_uuids,),
            )
            trade_summary = {
                row["run_uuid"]: dict(row)
                for row in cursor.fetchall()
            }

            cursor.execute(
                """
                SELECT
                    run_uuid::text,
                    trades,
                    wins,
                    losses,
                    expectancy,
                    profit_factor,
                    commission,
                    slippage,
                    verdict_code,
                    created_at
                FROM analytics.edge_observation_v1
                WHERE run_uuid::text = ANY(%s)
                ORDER BY created_at DESC
                """,
                (run_uuids,),
            )
            observations = [dict(row) for row in cursor.fetchall()]

            cursor.execute(
                """
                SELECT
                    table_schema,
                    table_name,
                    column_name
                FROM information_schema.columns
                WHERE table_schema = 'analytics'
                  AND (
                      table_name ILIKE '%error%'
                      OR table_name ILIKE '%failure%'
                      OR table_name ILIKE '%event%'
                      OR table_name ILIKE '%log%'
                      OR table_name ILIKE '%result%'
                  )
                ORDER BY
                    table_schema,
                    table_name,
                    ordinal_position
                """
            )
            diagnostic_objects = [
                dict(row)
                for row in cursor.fetchall()
            ]

            for run in runs:
                cursor.execute(
                    """
                    SELECT
                        count(*)::bigint AS bar_count,
                        min(ts) AS first_ts,
                        max(ts) AS last_ts
                    FROM public.market_bars
                    WHERE symbol = %s
                      AND timeframe = %s
                    """,
                    (
                        run["symbol"],
                        run["timeframe"],
                    ),
                )
                run["bar_coverage"] = dict(cursor.fetchone())

    observations_by_run: dict[str, list[dict[str, Any]]] = {}

    for row in observations:
        observations_by_run.setdefault(
            row["run_uuid"],
            [],
        ).append(row)

    unresolved: list[str] = []

    for run in runs:
        run_uuid = run["run_uuid"]
        trades = trade_summary.get(run_uuid)
        run_observations = observations_by_run.get(
            run_uuid,
            [],
        )
        bars = run["bar_coverage"]

        if str(run["status_code"]) == "FAILED":
            status_reason = "RUN_STATUS_FAILED"
        elif trades is None and not run_observations:
            status_reason = "RESULT_AND_TRADES_MISSING"
        elif trades is None:
            status_reason = "TRADE_PERSISTENCE_MISSING"
        elif not run_observations:
            status_reason = "OBSERVATION_PERSISTENCE_MISSING"
        else:
            status_reason = "RESULT_PRESENT"

        if int(bars["bar_count"] or 0) == 0:
            unresolved.append(
                f"NO_BARS:{run['symbol']}:{run['timeframe']}"
            )

        print(
            "FAILED_RUN "
            f"run_uuid={run_uuid} "
            f"status={run['status_code']} "
            f"strategy={run['strategy_code']} "
            f"symbol={run['symbol']} "
            f"timeframe={run['timeframe']} "
            f"runner={run['runner_version']} "
            f"source={run['source_version']} "
            f"reason={status_reason} "
            f"trade_count="
            f"{trades['trade_count'] if trades else 0} "
            f"observation_count={len(run_observations)} "
            f"bar_count={bars['bar_count']} "
            f"bar_first_ts={bars['first_ts']} "
            f"bar_last_ts={bars['last_ts']} "
            f"parameter_json="
            f"{json.dumps(run['parameter_json'], ensure_ascii=False, default=str)}"
        )

        for observation in run_observations:
            print(
                "OBSERVATION "
                f"run_uuid={run_uuid} "
                f"trades={observation['trades']} "
                f"expectancy={observation['expectancy']} "
                f"profit_factor={observation['profit_factor']} "
                f"verdict={observation['verdict_code']}"
            )

    object_names = sorted(
        {
            (
                row["table_schema"],
                row["table_name"],
            )
            for row in diagnostic_objects
        }
    )

    for schema_name, table_name in object_names:
        columns = [
            row["column_name"]
            for row in diagnostic_objects
            if row["table_schema"] == schema_name
            and row["table_name"] == table_name
        ]

        print(
            "DIAGNOSTIC_OBJECT "
            f"object={schema_name}.{table_name} "
            f"columns={','.join(columns)}"
        )

    print(f"run_count={len(runs)}")
    print(
        f"failed_run_count="
        f"{sum(str(row['status_code']) == 'FAILED' for row in runs)}"
    )
    print(
        f"trade_result_count="
        f"{len(trade_summary)}"
    )
    print(
        f"observation_count="
        f"{len(observations)}"
    )
    print(f"unresolved_count={len(unresolved)}")

    for item in unresolved:
        print(f"UNRESOLVED={item}")

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
        "POSTGRESQL_FUTURES_CONCRETE_FAILURE_DIAGNOSTICS_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

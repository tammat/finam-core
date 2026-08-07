#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


INFRASTRUCTURE_KEYS = {
    "bar_schema",
    "bar_table",
    "bar_limit",
    "minimum_bars",
    "market_regime",
    "quantity",
    "commission_per_side",
    "slippage_bps",
    "allow_short",
}


def parameter_keys(value: Any) -> set[str]:
    if not isinstance(value, dict):
        return set()

    return {
        str(key)
        for key in value
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "PostgreSQL Futures Strategy Parameter Contract Audit V1"
        )
    )
    parser.add_argument(
        "--strategy-code",
        default="RSI_MEAN_REVERSION_V1",
    )
    parser.add_argument(
        "--failed-batch-id",
        required=True,
    )
    args = parser.parse_args()

    with psycopg2.connect(build_psycopg_url()) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor,
        ) as cur:
            cur.execute(
                """
                SELECT
                    run_uuid::text,
                    research_batch_id,
                    research_code,
                    strategy_code,
                    symbol,
                    timeframe,
                    status_code,
                    runner_version,
                    source_version,
                    parameter_hash,
                    parameter_json,
                    created_at
                FROM analytics.edge_lab_run_v1
                WHERE research_batch_id = %s
                ORDER BY created_at, run_uuid
                """,
                (args.failed_batch_id,),
            )
            failed_rows = [
                dict(row)
                for row in cur.fetchall()
            ]

            if not failed_rows:
                raise SystemExit(
                    "ERROR=failed_batch_rows_missing:"
                    f"{args.failed_batch_id}"
                )

            cur.execute(
                """
                SELECT
                    r.run_uuid::text,
                    r.research_batch_id,
                    r.research_code,
                    r.strategy_code,
                    r.symbol,
                    r.timeframe,
                    r.status_code,
                    r.runner_version,
                    r.source_version,
                    r.parameter_hash,
                    r.parameter_json,
                    count(t.*)::bigint AS trade_count,
                    count(o.*)::bigint AS observation_count,
                    max(o.expectancy)::numeric AS expectancy,
                    max(o.profit_factor)::numeric AS profit_factor
                FROM analytics.edge_lab_run_v1 r
                LEFT JOIN analytics.research_trade_v1 t
                  ON t.run_uuid = r.run_uuid
                LEFT JOIN analytics.edge_observation_v1 o
                  ON o.run_uuid = r.run_uuid
                WHERE r.strategy_code = %s
                  AND r.parameter_json IS NOT NULL
                GROUP BY
                    r.run_uuid,
                    r.research_batch_id,
                    r.research_code,
                    r.strategy_code,
                    r.symbol,
                    r.timeframe,
                    r.status_code,
                    r.runner_version,
                    r.source_version,
                    r.parameter_hash,
                    r.parameter_json,
                    r.created_at
                ORDER BY
                    count(t.*) DESC,
                    count(o.*) DESC,
                    r.created_at DESC
                LIMIT 500
                """,
                (args.strategy_code,),
            )
            strategy_rows = [
                dict(row)
                for row in cur.fetchall()
            ]

    failed = failed_rows[0]
    failed_parameters = dict(
        failed["parameter_json"] or {}
    )
    failed_keys = parameter_keys(failed_parameters)
    failed_strategy_keys = (
        failed_keys - INFRASTRUCTURE_KEYS
    )

    successful_rows = [
        row
        for row in strategy_rows
        if int(row["trade_count"] or 0) > 0
        and int(row["observation_count"] or 0) > 0
    ]

    key_frequency: Counter[str] = Counter()

    for row in successful_rows:
        keys = (
            parameter_keys(row["parameter_json"])
            - INFRASTRUCTURE_KEYS
        )
        key_frequency.update(keys)

    required_candidate_keys = {
        key
        for key, count in key_frequency.items()
        if count == len(successful_rows)
    } if successful_rows else set()

    missing_candidate_keys = sorted(
        required_candidate_keys
        - failed_strategy_keys
    )

    print(
        "=== POSTGRESQL FUTURES STRATEGY "
        "PARAMETER CONTRACT AUDIT V1 ==="
    )
    print(f"failed_batch_id={args.failed_batch_id}")
    print(f"strategy_code={args.strategy_code}")
    print(f"failed_run_uuid={failed['run_uuid']}")
    print(f"failed_symbol={failed['symbol']}")
    print(f"failed_timeframe={failed['timeframe']}")
    print(f"failed_status={failed['status_code']}")
    print(
        "failed_parameter_json="
        + json.dumps(
            failed_parameters,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
    )
    print(
        "failed_parameter_keys="
        + ",".join(sorted(failed_keys))
    )
    print(
        "failed_strategy_parameter_keys="
        + ",".join(sorted(failed_strategy_keys))
    )
    print(
        f"strategy_run_count={len(strategy_rows)}"
    )
    print(
        f"successful_strategy_run_count="
        f"{len(successful_rows)}"
    )
    print(
        "required_candidate_keys="
        + ",".join(sorted(required_candidate_keys))
    )
    print(
        "missing_candidate_keys="
        + ",".join(missing_candidate_keys)
    )

    for row in successful_rows[:20]:
        parameters = dict(row["parameter_json"] or {})

        print(
            "SUCCESSFUL_TEMPLATE "
            f"run_uuid={row['run_uuid']} "
            f"symbol={row['symbol']} "
            f"timeframe={row['timeframe']} "
            f"trades={row['trade_count']} "
            f"observations={row['observation_count']} "
            f"expectancy={row['expectancy']} "
            f"profit_factor={row['profit_factor']} "
            f"runner={row['runner_version']} "
            f"source={row['source_version']} "
            "parameter_json="
            + json.dumps(
                parameters,
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
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

    if not successful_rows:
        print(
            "root_cause="
            "NO_SUCCESSFUL_STRATEGY_TEMPLATE"
        )
        print(
            "VERDICT="
            "POSTGRESQL_FUTURES_STRATEGY_PARAMETER_CONTRACT_V1_BLOCKED"
        )
        return 2

    if missing_candidate_keys:
        print(
            "root_cause="
            "INCOMPLETE_STRATEGY_PARAMETER_CONTRACT"
        )
        print(
            "VERDICT="
            "POSTGRESQL_FUTURES_STRATEGY_PARAMETER_CONTRACT_V1_GAP_CONFIRMED"
        )
        return 0

    print(
        "root_cause="
        "PARAMETER_CONTRACT_NOT_CONFIRMED"
    )
    print(
        "VERDICT="
        "POSTGRESQL_FUTURES_STRATEGY_PARAMETER_CONTRACT_V1_UNRESOLVED"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

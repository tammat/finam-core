#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg2
from psycopg2.extras import Json, RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


SOURCE_VERSION = "POSTGRESQL_FUTURES_CONCRETE_CONTRACT_BACKTEST_V1"


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "PostgreSQL Futures Concrete Contract Backtest V1"
        )
    )
    parser.add_argument(
        "--continuous-symbol",
        default="NG@RTSX",
    )
    parser.add_argument(
        "--contract-symbol",
        required=True,
    )
    parser.add_argument(
        "--strategy-code",
        default="RSI_MEAN_REVERSION_V1",
    )
    parser.add_argument(
        "--timeframe",
        default="M5",
    )
    parser.add_argument(
        "--batch-id",
        required=True,
    )
    parser.add_argument(
        "--save",
        action="store_true",
    )
    args = parser.parse_args()

    if args.contract_symbol == args.continuous_symbol:
        raise SystemExit(
            "ERROR=contract_symbol_equals_continuous_symbol"
        )

    if not args.contract_symbol.endswith("@RTSX"):
        raise SystemExit(
            "ERROR=contract_symbol_not_rtsx:"
            f"{args.contract_symbol}"
        )

    with psycopg2.connect(build_psycopg_url()) as conn:
        if not args.save:
            conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor,
        ) as cursor:
            cursor.execute(
                """
                SELECT
                    run_uuid::text,
                    research_code,
                    strategy_code,
                    strategy_version,
                    symbol,
                    timeframe,
                    parameter_json,
                    parameter_hash,
                    dataset_version,
                    runner_version,
                    source_version
                FROM analytics.edge_lab_run_v1
                WHERE symbol = %s
                  AND strategy_code = %s
                  AND timeframe = %s
                  AND parameter_json IS NOT NULL
                ORDER BY
                    CASE
                        WHEN status_code = 'DONE' THEN 0
                        WHEN status_code = 'SUPERSEDED' THEN 1
                        ELSE 2
                    END,
                    created_at DESC,
                    run_uuid
                LIMIT 1
                """,
                (
                    args.continuous_symbol,
                    args.strategy_code,
                    args.timeframe,
                ),
            )

            template = cursor.fetchone()

            if template is None:
                raise SystemExit(
                    "ERROR=continuous_symbol_template_missing:"
                    f"{args.continuous_symbol}:"
                    f"{args.strategy_code}:"
                    f"{args.timeframe}"
                )

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
                    args.contract_symbol,
                    args.timeframe,
                ),
            )

            coverage = cursor.fetchone()

            if int(coverage["bar_count"] or 0) < 100:
                raise SystemExit(
                    "ERROR=insufficient_contract_bars:"
                    f"{args.contract_symbol}:"
                    f"{args.timeframe}:"
                    f"{coverage['bar_count']}"
                )

            parameter_json = dict(
                template["parameter_json"] or {}
            )

            parameter_json["bar_schema"] = "public"
            parameter_json["bar_table"] = "market_bars"
            parameter_json["market_regime"] = (
                "FUTURES_CONCRETE_CONTRACT_BACKTEST_V1"
            )

            # parameter_hash отражает стратегию и параметры.
            # Символ входит в полную идентичность edge_lab_run_v1.
            parameter_hash = hashlib.md5(
                (
                    args.strategy_code
                    + "|"
                    + canonical_json(parameter_json)
                ).encode("utf-8")
            ).hexdigest()

            run_uuid = str(uuid.uuid4())

            identity_seed = hashlib.sha256(
                (
                    args.batch_id
                    + "|"
                    + args.strategy_code
                    + "|"
                    + args.contract_symbol
                    + "|"
                    + args.timeframe
                    + "|"
                    + parameter_hash
                ).encode("utf-8")
            ).hexdigest()[:12]

            research_code = (
                "PG_FUTURES_CONCRETE_V1:"
                f"{identity_seed}:"
                f"{args.strategy_code}:"
                f"{args.contract_symbol}:"
                f"{args.timeframe}"
            )

            dataset_version = str(
                template["dataset_version"] or "default"
            )

            existing_count = 0
            inserted_count = 0

            cursor.execute(
                """
                SELECT count(*)::bigint AS existing_count
                FROM analytics.edge_lab_run_v1
                WHERE research_code = %s
                  AND strategy_code = %s
                  AND symbol = %s
                  AND timeframe = %s
                  AND parameter_hash = %s
                  AND dataset_version = %s
                """,
                (
                    research_code,
                    args.strategy_code,
                    args.contract_symbol,
                    args.timeframe,
                    parameter_hash,
                    dataset_version,
                ),
            )

            existing_count = int(
                cursor.fetchone()["existing_count"] or 0
            )

            if args.save and existing_count == 0:
                cursor.execute(
                    """
                    INSERT INTO analytics.edge_lab_run_v1 (
                        run_uuid,
                        research_batch_id,
                        research_code,
                        strategy_code,
                        strategy_version,
                        symbol,
                        timeframe,
                        status_code,
                        parameter_hash,
                        parameter_json,
                        dataset_version,
                        runner_version,
                        source_version,
                        created_at,
                        started_at,
                        finished_at
                    )
                    VALUES (
                        %s::uuid,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        'QUEUED',
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        NULL,
                        NULL
                    )
                    """,
                    (
                        run_uuid,
                        args.batch_id,
                        research_code,
                        args.strategy_code,
                        template["strategy_version"],
                        args.contract_symbol,
                        args.timeframe,
                        parameter_hash,
                        Json(parameter_json),
                        dataset_version,
                        (
                            "POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1"
                        ),
                        SOURCE_VERSION,
                        datetime.now(timezone.utc),
                    ),
                )

                inserted_count = cursor.rowcount

    print(
        "=== POSTGRESQL FUTURES "
        "CONCRETE CONTRACT BACKTEST V1 ==="
    )
    print(
        f"continuous_symbol="
        f"{args.continuous_symbol}"
    )
    print(
        f"contract_symbol="
        f"{args.contract_symbol}"
    )
    print(f"strategy_code={args.strategy_code}")
    print(f"timeframe={args.timeframe}")
    print(f"batch_id={args.batch_id}")
    print(f"template_run_uuid={template['run_uuid']}")
    print(f"run_uuid={run_uuid}")
    print(f"research_code={research_code}")
    print(f"parameter_hash={parameter_hash}")
    print(f"dataset_version={dataset_version}")
    print(f"bar_count={coverage['bar_count']}")
    print(f"bar_first_ts={coverage['first_ts']}")
    print(f"bar_last_ts={coverage['last_ts']}")
    print(f"existing_count={existing_count}")
    print(f"inserted_count={inserted_count}")
    print(
        f"db_writes_performed="
        f"{1 if args.save and inserted_count else 0}"
    )
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

    if existing_count > 0:
        print(
            "VERDICT="
            "POSTGRESQL_FUTURES_CONCRETE_CONTRACT_TASK_EXISTS"
        )
        return 0

    if args.save:
        print(
            "VERDICT="
            "POSTGRESQL_FUTURES_CONCRETE_CONTRACT_TASK_CREATED"
        )
    else:
        print(
            "VERDICT="
            "POSTGRESQL_FUTURES_CONCRETE_CONTRACT_TASK_DRY_RUN_OK"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

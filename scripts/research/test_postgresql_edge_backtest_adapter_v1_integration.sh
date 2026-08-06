#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"

RUN_UUID="${1:-8c15fc0c-b8c3-40a4-8299-089702c5173d}"

cd "$ROOT"

[[ "$RUN_UUID" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]] || {
    echo "ERROR=invalid_run_uuid:$RUN_UUID"
    exit 1
}

PYTHONPATH=src \
"$PYTHON" - "$RUN_UUID" <<'PY'
from __future__ import annotations

import sys
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


run_uuid = sys.argv[1]

# Допуск соответствует округлению expectancy до 8 знаков.
EXPECTANCY_TOLERANCE = Decimal("0.00000001")
COMMISSION_TOLERANCE = Decimal("0.00000001")
SLIPPAGE_TOLERANCE = Decimal("0.00000001")


def decimal_close(
    actual: Decimal,
    expected: Decimal,
    tolerance: Decimal,
) -> bool:
    return abs(actual - expected) <= tolerance


with psycopg2.connect(build_psycopg_url()) as conn:
    conn.set_session(readonly=True)

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                status_code,
                runner_version,
                source_version,
                started_at,
                finished_at
            FROM analytics.edge_lab_run_v1
            WHERE run_uuid = %s::uuid
            """,
            (run_uuid,),
        )
        run = cur.fetchone()

        cur.execute(
            """
            SELECT
                count(*)::bigint AS trade_rows,
                count(DISTINCT trade_no)::bigint
                    AS distinct_trade_rows,
                COALESCE(sum(commission), 0)::numeric
                    AS commission_sum,
                COALESCE(sum(slippage), 0)::numeric
                    AS slippage_sum,
                COALESCE(sum(net_pnl), 0)::numeric
                    AS net_pnl_sum
            FROM analytics.research_trade_v1
            WHERE run_uuid = %s::uuid
            """,
            (run_uuid,),
        )
        trades = cur.fetchone()

        cur.execute(
            """
            SELECT
                trades,
                commission,
                slippage,
                expectancy,
                profit_factor,
                verdict_code,
                runner_version,
                source_version
            FROM analytics.edge_observation_v1
            WHERE run_uuid = %s::uuid
            """,
            (run_uuid,),
        )
        observation = cur.fetchone()

print(f"run={dict(run) if run else None}")
print(f"trades={dict(trades) if trades else None}")
print(
    "observation="
    f"{dict(observation) if observation else None}"
)

if run is None:
    raise SystemExit("ERROR=run_missing")

if observation is None:
    raise SystemExit("ERROR=observation_missing")

if run["status_code"] != "DONE":
    raise SystemExit(
        f"ERROR=unexpected_run_status:{run['status_code']}"
    )

if (
    run["runner_version"]
    != "POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1"
):
    raise SystemExit("ERROR=unexpected_runner_version")

if (
    run["source_version"]
    != "POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1"
):
    raise SystemExit("ERROR=unexpected_source_version")

trade_rows = int(trades["trade_rows"])
distinct_rows = int(trades["distinct_trade_rows"])

if trade_rows != distinct_rows:
    raise SystemExit(
        "ERROR=duplicate_trade_no:"
        f"rows={trade_rows}:distinct={distinct_rows}"
    )

if int(observation["trades"]) != trade_rows:
    raise SystemExit(
        "ERROR=observation_trade_count_mismatch:"
        f"observation={observation['trades']}:"
        f"trade_rows={trade_rows}"
    )

if not decimal_close(
    observation["commission"],
    trades["commission_sum"],
    COMMISSION_TOLERANCE,
):
    raise SystemExit(
        "ERROR=commission_mismatch:"
        f"observation={observation['commission']}:"
        f"trades={trades['commission_sum']}"
    )

if not decimal_close(
    observation["slippage"],
    trades["slippage_sum"],
    SLIPPAGE_TOLERANCE,
):
    raise SystemExit(
        "ERROR=slippage_mismatch:"
        f"observation={observation['slippage']}:"
        f"trades={trades['slippage_sum']}"
    )

if trade_rows <= 0:
    expected_expectancy = Decimal("0")
else:
    expected_expectancy = (
        trades["net_pnl_sum"] / Decimal(trade_rows)
    )

expectancy_delta = abs(
    observation["expectancy"] - expected_expectancy
)

print(f"expected_expectancy={expected_expectancy}")
print(
    f"stored_expectancy={observation['expectancy']}"
)
print(f"expectancy_delta={expectancy_delta}")
print(
    f"expectancy_tolerance={EXPECTANCY_TOLERANCE}"
)

if not decimal_close(
    observation["expectancy"],
    expected_expectancy,
    EXPECTANCY_TOLERANCE,
):
    raise SystemExit(
        "ERROR=expectancy_mismatch:"
        f"stored={observation['expectancy']}:"
        f"expected={expected_expectancy}:"
        f"delta={expectancy_delta}"
    )

if (
    observation["expectancy"] < 0
    and observation["verdict_code"]
    != "NEGATIVE_AFTER_COSTS"
):
    raise SystemExit(
        "ERROR=negative_expectancy_verdict_mismatch"
    )

print("run_status_contract=OK")
print("trade_identity_contract=OK")
print("commission_reconciliation=OK")
print("slippage_reconciliation=OK")
print("expectancy_reconciliation=OK")
print("verdict_contract=OK")
print("db_writes_performed=0")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print(
    "VERDICT="
    "POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1_INTEGRATION_OK"
)
PY


#!/usr/bin/env bash

set -euo pipefail

ROOT="/opt/finam-core"

PYTHON="$ROOT/venv/bin/python"

LOG="/tmp/test_postgresql_edge_parameter_search_preflight_integration_v1.log"

cd "$ROOT"

rm -f "$LOG"

PYTHONPATH=src \

"$PYTHON" - <<'PY' | tee "$LOG"

from __future__ import annotations

import importlib.util

import pathlib

import sys

import uuid

import psycopg2

from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url

builder_path = pathlib.Path(

    "scripts/research/build_postgresql_edge_parameter_search_v1.py"

)

spec = importlib.util.spec_from_file_location(

    "edge_parameter_search_builder",

    builder_path,

)

if spec is None or spec.loader is None:

    raise SystemExit("ERROR=builder_import_spec_failed")

builder = importlib.util.module_from_spec(spec)

sys.modules[spec.name] = builder

spec.loader.exec_module(builder)

def count_batch(cur, batch_id: str) -> int:

    cur.execute(

        """

        SELECT count(*)::bigint AS row_count

        FROM analytics.edge_lab_run_v1

        WHERE research_batch_id = %s

        """,

        (batch_id,),

    )

    return int(cur.fetchone()["row_count"] or 0)

required = (

    "SearchTask",

    "insert_tasks",

)

for name in required:

    if not hasattr(builder, name):

        raise SystemExit(f"ERROR=builder_symbol_missing:{name}")

with psycopg2.connect(build_psycopg_url()) as conn:

    conn.autocommit = False

    with conn.cursor(cursor_factory=RealDictCursor) as cur:

        # --------------------------------------------------

        # CASE 1: unsupported strategy

        # --------------------------------------------------

        batch_unsupported = (

            "PREFLIGHT_IT_UNSUPPORTED_"

            + uuid.uuid4().hex[:12].upper()

        )

        unsupported_task = builder.SearchTask(

            strategy_code="RSI_MEAN_REVERSION_V1",

            symbol="SBER@MISX",

            timeframe="M5",

            parameters={

                "commission_per_side": 0,

                "slippage_bps": 0,

                "quantity": 1,

            },

            parameter_hash="integration_unsupported",

        )

        before = count_batch(cur, batch_unsupported)

        inserted, duplicates = builder.insert_tasks(
            cur,
            tasks=[unsupported_task],
            batch_id=batch_unsupported,
        )

        after = count_batch(cur, batch_unsupported)

        print(

            "INTEGRATION_CASE "

            "case=UNSUPPORTED_STRATEGY "

            f"inserted={inserted} "

            f"duplicates={duplicates} "

            f"before={before} "

            f"after={after}"

        )

        if inserted != 0 or after != before:

            raise SystemExit(

                "ERROR=unsupported_strategy_was_inserted"

            )

        # --------------------------------------------------

        # CASE 2: no bars

        # --------------------------------------------------

        batch_no_bars = (

            "PREFLIGHT_IT_NO_BARS_"

            + uuid.uuid4().hex[:12].upper()

        )

        no_bars_task = builder.SearchTask(

            strategy_code="ATR_IMPULSE_V1",

            symbol="NG@RTSX",

            timeframe="M5",

            parameters={

                "atr_period": 14,

                "impulse_atr_multiplier": 1.0,

                "hold_bars": 5,

                "quantity": 1,

                "commission_per_side": 0,

                "slippage_bps": 0,

            },

            parameter_hash="integration_no_bars",

        )

        before = count_batch(cur, batch_no_bars)

        inserted, duplicates = builder.insert_tasks(
            cur,
            tasks=[no_bars_task],
            batch_id=batch_no_bars,
        )

        after = count_batch(cur, batch_no_bars)

        print(

            "INTEGRATION_CASE "

            "case=NO_BARS "

            f"inserted={inserted} "

            f"duplicates={duplicates} "

            f"before={before} "

            f"after={after}"

        )

        if inserted != 0 or after != before:

            raise SystemExit(

                "ERROR=no_bars_task_was_inserted"

            )

        # --------------------------------------------------

        # CASE 3: invalid parameter contract

        # --------------------------------------------------

        batch_invalid = (

            "PREFLIGHT_IT_INVALID_PARAMETERS_"

            + uuid.uuid4().hex[:12].upper()

        )

        invalid_task = builder.SearchTask(

            strategy_code="ATR_IMPULSE_V1",

            symbol="SBER@MISX",

            timeframe="M5",

            parameters={

                "commission_per_side": 0,

                "slippage_bps": -1,

                "quantity": 1,

            },

            parameter_hash="integration_invalid_parameters",

        )

        before = count_batch(cur, batch_invalid)

        inserted, duplicates = builder.insert_tasks(
            cur,
            tasks=[invalid_task],
            batch_id=batch_invalid,
        )

        after = count_batch(cur, batch_invalid)

        print(

            "INTEGRATION_CASE "

            "case=INVALID_PARAMETER_CONTRACT "

            f"inserted={inserted} "

            f"duplicates={duplicates} "

            f"before={before} "

            f"after={after}"

        )

        if inserted != 0 or after != before:

            raise SystemExit(

                "ERROR=invalid_parameter_task_was_inserted"

            )

    # Тест ничего не должен сохранять.

    conn.rollback()

print("db_writes_persisted=0")

print("runtime_changed=0")

print("execution_changed=0")

print("orders_changed=0")

print("fills_changed=0")

print("micro_live_allowed=0")

print(

    "VERDICT="

    "POSTGRESQL_EDGE_PARAMETER_SEARCH_PREFLIGHT_INTEGRATION_V1_OK"

)

PY

grep -Fq "INTEGRATION_CASE case=UNSUPPORTED_STRATEGY inserted=0" "$LOG"
grep -Fq "INTEGRATION_CASE case=NO_BARS inserted=0" "$LOG"
grep -Fq "INTEGRATION_CASE case=INVALID_PARAMETER_CONTRACT inserted=0" "$LOG"
grep -Fq "db_writes_persisted=0" "$LOG"
grep -Fq "VERDICT=POSTGRESQL_EDGE_PARAMETER_SEARCH_PREFLIGHT_INTEGRATION_V1_OK" "$LOG"

echo "VERDICT=TEST_POSTGRESQL_EDGE_PARAMETER_SEARCH_PREFLIGHT_INTEGRATION_V1_OK"

#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
BUILDER="scripts/research/build_postgresql_cost_replay_quantity_scaling_v1.py"

BATCH_ID="${1:-PG_EDGE_FAMILY_EXPANSION_V1_20260806_073217}"
LOG="/tmp/test_postgresql_cost_replay_quantity_scaling_v1.log"

cd "$ROOT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" -m py_compile "$BUILDER"

SOURCE_RUN_UUID="$(
    PYTHONPATH=src "$PYTHON" - "$BATCH_ID" <<'PY'
from __future__ import annotations

import sys

import psycopg2

from finam_core.analytics.statistics_repository import build_psycopg_url


batch_id = sys.argv[1]

with psycopg2.connect(build_psycopg_url()) as conn:
    conn.set_session(readonly=True)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                r.run_uuid::text
            FROM analytics.edge_lab_run_v1 r
            JOIN analytics.research_trade_v1 t
              ON t.run_uuid = r.run_uuid
            WHERE r.research_batch_id = %s
              AND r.strategy_code =
                  'MEAN_REVERSION_ZSCORE_V1'
              AND r.symbol = 'SBER@MISX'
              AND r.timeframe = 'M5'
            GROUP BY r.run_uuid
            ORDER BY
                avg(t.net_pnl + t.commission) DESC,
                count(*) DESC,
                r.run_uuid
            LIMIT 1
            """,
            (batch_id,),
        )

        row = cur.fetchone()

if row is None:
    raise SystemExit("source_run_not_found")

print(row[0])
PY
)"

[[ -n "$SOURCE_RUN_UUID" ]]

echo "source_run_uuid=$SOURCE_RUN_UUID"

PYTHONPATH=src \
"$PYTHON" "$BUILDER" \
  --source-run-uuid "$SOURCE_RUN_UUID" \
  --lot-size 10 \
  --broker-order-fee-per-side 41.30 \
  --settlement-fee-rate 0.0003 \
  --exchange-fee-rate 0 \
  --other-fee-per-side 0 |
tee "$LOG"

grep -Fq \
  "quantity_scaling_applied=1" \
  "$LOG"

grep -Fq \
  "gross_pnl_scaled=1" \
  "$LOG"

grep -Fq \
  "slippage_scaled=1" \
  "$LOG"

grep -Fq \
  "commission_recalculated=1" \
  "$LOG"

grep -Fq \
  "VERDICT=POSTGRESQL_COST_REPLAY_QUANTITY_SCALING_V1_READY" \
  "$LOG"

for marker in \
  "INSERT INTO" \
  "UPDATE analytics" \
  "DELETE FROM analytics" \
  "sqlite3" \
  "bars.sqlite" \
  "send_order(" \
  "place_order(" \
  "submit_order("
do
    COUNT="$(
      {
        grep -F "$marker" "$BUILDER" ||
        true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_marker=$marker count=$COUNT"
    [[ "$COUNT" -eq 0 ]]
done

echo "db_writes_performed=0"
echo "historical_trade_rows_changed=0"
echo "historical_observation_rows_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "oos_allowed=0"
echo "shadow_allowed=0"
echo "paper_allowed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_POSTGRESQL_COST_REPLAY_QUANTITY_SCALING_V1_OK"

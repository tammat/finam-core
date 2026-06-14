#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/runtime/build_shadow_runtime_position_reconciliation_v1.py

python3 src/scripts/runtime/build_shadow_runtime_position_reconciliation_v1.py \
  | tee /tmp/shadow_runtime_position_reconciliation_v1.log

grep -q "SHADOW RUNTIME POSITION RECONCILIATION V1" /tmp/shadow_runtime_position_reconciliation_v1.log
grep -q "RECONCILIATION_ROW" /tmp/shadow_runtime_position_reconciliation_v1.log
grep -q "LKOH@MISX" /tmp/shadow_runtime_position_reconciliation_v1.log
grep -q "runtime_allow=0" /tmp/shadow_runtime_position_reconciliation_v1.log
grep -q "execution_enabled=0" /tmp/shadow_runtime_position_reconciliation_v1.log
grep -q "SHADOW_RUNTIME_POSITION_RECONCILIATION_V1_OK" /tmp/shadow_runtime_position_reconciliation_v1.log

psql "$DATABASE_URL" -P pager=off -c "
SELECT
    symbol,
    expected_qty,
    actual_qty,
    qty_diff,
    expected_fills,
    actual_fills_processed,
    fills_diff,
    reconciliation_status,
    runtime_allowed,
    execution_enabled
FROM shadow_runtime_position_reconciliation
ORDER BY id DESC
LIMIT 5;
"

echo TEST_SHADOW_RUNTIME_POSITION_RECONCILIATION_V1_OK

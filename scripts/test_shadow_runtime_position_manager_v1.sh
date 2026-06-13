#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/runtime/build_shadow_runtime_position_manager_v1.py

python3 src/scripts/runtime/build_shadow_runtime_position_manager_v1.py \
  | tee /tmp/shadow_runtime_position_manager_v1.log

grep -q "SHADOW RUNTIME POSITION MANAGER V1" /tmp/shadow_runtime_position_manager_v1.log
grep -q "POSITION_ROW" /tmp/shadow_runtime_position_manager_v1.log
grep -q "LKOH@MISX" /tmp/shadow_runtime_position_manager_v1.log
grep -q "runtime_allow=0" /tmp/shadow_runtime_position_manager_v1.log
grep -q "execution_enabled=0" /tmp/shadow_runtime_position_manager_v1.log
grep -q "SHADOW_RUNTIME_POSITION_MANAGER_V1_OK" /tmp/shadow_runtime_position_manager_v1.log

psql "$DATABASE_URL" -P pager=off -c "
SELECT
    symbol,
    qty,
    avg_price,
    fills_processed,
    last_fill_id,
    runtime_allowed,
    execution_enabled
FROM shadow_runtime_positions
ORDER BY symbol;
"

echo TEST_SHADOW_RUNTIME_POSITION_MANAGER_V1_OK

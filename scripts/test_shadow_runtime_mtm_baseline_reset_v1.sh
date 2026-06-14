#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/runtime/build_shadow_runtime_mtm_baseline_reset_v1.py

python3 src/scripts/runtime/build_shadow_runtime_mtm_baseline_reset_v1.py \
  | tee /tmp/shadow_runtime_mtm_baseline_reset_v1.log

grep -q "SHADOW RUNTIME MTM BASELINE RESET V1" /tmp/shadow_runtime_mtm_baseline_reset_v1.log
grep -q "BASELINE_ROW" /tmp/shadow_runtime_mtm_baseline_reset_v1.log
grep -q "LKOH@MISX" /tmp/shadow_runtime_mtm_baseline_reset_v1.log
grep -q "BASELINE_RESET" /tmp/shadow_runtime_mtm_baseline_reset_v1.log
grep -q "new_drawdown=0" /tmp/shadow_runtime_mtm_baseline_reset_v1.log
grep -q "runtime_allow=0" /tmp/shadow_runtime_mtm_baseline_reset_v1.log
grep -q "execution_enabled=0" /tmp/shadow_runtime_mtm_baseline_reset_v1.log
grep -q "SHADOW_RUNTIME_MTM_BASELINE_RESET_V1_OK" /tmp/shadow_runtime_mtm_baseline_reset_v1.log

psql "$DATABASE_URL" -P pager=off -c "
SELECT
    symbol,
    old_max_equity,
    old_drawdown,
    new_max_equity,
    new_drawdown,
    current_equity,
    baseline_status,
    runtime_allowed,
    execution_enabled
FROM shadow_runtime_mtm_baseline_reset
ORDER BY id DESC
LIMIT 5;
"

echo TEST_SHADOW_RUNTIME_MTM_BASELINE_RESET_V1_OK

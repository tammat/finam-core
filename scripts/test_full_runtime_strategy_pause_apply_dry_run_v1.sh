#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST FULL RUNTIME STRATEGY PAUSE APPLY DRY RUN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_full_runtime_strategy_pause_apply_dry_run_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_full_runtime_strategy_pause_apply_dry_run_v1.py \
  | tee /tmp/full_runtime_strategy_pause_apply_dry_run_v1.log

grep -q "FULL_RUNTIME_STRATEGY_PAUSE_APPLY_DRY_RUN_V1_OK" /tmp/full_runtime_strategy_pause_apply_dry_run_v1.log
grep -q "FULL_RUNTIME_PAUSE_APPLY_DRY_RUN_SUMMARY" /tmp/full_runtime_strategy_pause_apply_dry_run_v1.log
grep -q "planned_updates=" /tmp/full_runtime_strategy_pause_apply_dry_run_v1.log
grep -q "db_update=0" /tmp/full_runtime_strategy_pause_apply_dry_run_v1.log
grep -q "recommended_apply_requires_manual_confirmation=1" /tmp/full_runtime_strategy_pause_apply_dry_run_v1.log
grep -q "VERDICT=" /tmp/full_runtime_strategy_pause_apply_dry_run_v1.log

echo
echo "=== FULL RUNTIME PAUSE APPLY DRY RUN SUMMARY ==="
grep -E "FULL_RUNTIME_PAUSE_APPLY_DRY_RUN_ROW|planned_updates=|runtime_changes_required=|VERDICT=" \
  /tmp/full_runtime_strategy_pause_apply_dry_run_v1.log

echo TEST_FULL_RUNTIME_STRATEGY_PAUSE_APPLY_DRY_RUN_V1_OK

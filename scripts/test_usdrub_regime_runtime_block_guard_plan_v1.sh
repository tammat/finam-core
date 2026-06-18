#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST USDRUB REGIME RUNTIME BLOCK GUARD PLAN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_usdrub_regime_runtime_block_guard_plan_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_usdrub_regime_runtime_block_guard_plan_v1.py \
  | tee /tmp/usdrub_regime_runtime_block_guard_plan_v1.log

grep -q "USDRUB_REGIME_RUNTIME_BLOCK_GUARD_PLAN_V1_OK" /tmp/usdrub_regime_runtime_block_guard_plan_v1.log
grep -q "USDRUB_RUNTIME_BLOCK_GUARD_PLAN_SUMMARY" /tmp/usdrub_regime_runtime_block_guard_plan_v1.log
grep -q "recommended_patch_file=src/finam_core/pipelines/paper_pipeline.py" /tmp/usdrub_regime_runtime_block_guard_plan_v1.log
grep -q "recommended_guard_function=_is_runtime_strategy_blocked_v1" /tmp/usdrub_regime_runtime_block_guard_plan_v1.log
grep -q "db_update=0" /tmp/usdrub_regime_runtime_block_guard_plan_v1.log
grep -q "VERDICT=" /tmp/usdrub_regime_runtime_block_guard_plan_v1.log

echo
echo "=== USDRUB REGIME RUNTIME BLOCK GUARD PLAN SUMMARY ==="
grep -E "USDRUB_RUNTIME_BLOCK_SELECTION_ROW|trades_today=|blocked_selection_rows=|recommended_|VERDICT=" \
  /tmp/usdrub_regime_runtime_block_guard_plan_v1.log | head -120

echo TEST_USDRUB_REGIME_RUNTIME_BLOCK_GUARD_PLAN_V1_OK

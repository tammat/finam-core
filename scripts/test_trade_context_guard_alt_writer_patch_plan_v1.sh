#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TRADE CONTEXT GUARD ALT WRITER PATCH PLAN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_trade_context_guard_alt_writer_patch_plan_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_trade_context_guard_alt_writer_patch_plan_v1.py \
  | tee /tmp/trade_context_guard_alt_writer_patch_plan_v1.log

grep -q "TRADE_CONTEXT_GUARD_ALT_WRITER_PATCH_PLAN_V1_OK" /tmp/trade_context_guard_alt_writer_patch_plan_v1.log
grep -q "TRADE_CONTEXT_GUARD_ALT_WRITER_PATCH_PLAN_SUMMARY" /tmp/trade_context_guard_alt_writer_patch_plan_v1.log
grep -q "log_trade_object_calls=" /tmp/trade_context_guard_alt_writer_patch_plan_v1.log
grep -q "needs_patch=" /tmp/trade_context_guard_alt_writer_patch_plan_v1.log
grep -q "db_update=0" /tmp/trade_context_guard_alt_writer_patch_plan_v1.log
grep -q "VERDICT=" /tmp/trade_context_guard_alt_writer_patch_plan_v1.log

echo
echo "=== ALT WRITER PATCH PLAN SUMMARY ==="
grep -E "PATCH_PLAN_LOG_TRADE_OBJECT_CALL|log_trade_object_calls=|context_helper_hits=|needs_patch=|VERDICT=" \
  /tmp/trade_context_guard_alt_writer_patch_plan_v1.log

echo TEST_TRADE_CONTEXT_GUARD_ALT_WRITER_PATCH_PLAN_V1_OK

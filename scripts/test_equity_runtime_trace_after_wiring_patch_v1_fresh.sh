#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY RUNTIME TRACE AFTER WIRING PATCH V1 FRESH ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_equity_runtime_trace_after_wiring_patch_v1.py

EQUITY_TRACE_SYMBOL="${EQUITY_TRACE_SYMBOL:-SBER@MISX}" \
EQUITY_TRACE_STRATEGY="${EQUITY_TRACE_STRATEGY:-VOLATILITY_BREAKOUT_EQUITY}" \
EQUITY_TRACE_SINCE_INTERVAL="${EQUITY_TRACE_SINCE_INTERVAL:-15 minutes}" \
PYTHONPATH=src python3 src/scripts/runtime/build_equity_runtime_trace_after_wiring_patch_v1.py \
  | tee /tmp/equity_runtime_trace_after_wiring_patch_v1_fresh.log

grep -q "EQUITY_RUNTIME_TRACE_AFTER_WIRING_PATCH_V1_OK" /tmp/equity_runtime_trace_after_wiring_patch_v1_fresh.log
grep -q "EQUITY_RUNTIME_AFTER_PATCH_RUNTIME_ROW" /tmp/equity_runtime_trace_after_wiring_patch_v1_fresh.log
grep -q "EQUITY_RUNTIME_AFTER_PATCH_SUMMARY" /tmp/equity_runtime_trace_after_wiring_patch_v1_fresh.log
grep -q "runtime_strategy=VOLATILITY_BREAKOUT_EQUITY" /tmp/equity_runtime_trace_after_wiring_patch_v1_fresh.log
grep -q "db_update=0" /tmp/equity_runtime_trace_after_wiring_patch_v1_fresh.log
grep -q "VERDICT=" /tmp/equity_runtime_trace_after_wiring_patch_v1_fresh.log

echo
echo "=== EQUITY RUNTIME TRACE AFTER WIRING PATCH V1 FRESH SUMMARY ==="
grep -E "service_active_since=|runtime_strategy=|fresh_guard_rows=|fresh_expected_strategy_rows=|fresh_other_strategy_rows=|last_guard_created_at=|diagnosis=|VERDICT=" \
  /tmp/equity_runtime_trace_after_wiring_patch_v1_fresh.log

echo TEST_EQUITY_RUNTIME_TRACE_AFTER_WIRING_PATCH_V1_FRESH_OK

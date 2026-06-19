#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY PRE SIGNAL GUARD PATCH PLAN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_equity_pre_signal_guard_patch_plan_v1.py

PYTHONPATH=src python3 src/scripts/research/build_equity_pre_signal_guard_patch_plan_v1.py \
  | tee /tmp/equity_pre_signal_guard_patch_plan_v1.log

grep -q "EQUITY_PRE_SIGNAL_GUARD_PATCH_PLAN_V1_OK" /tmp/equity_pre_signal_guard_patch_plan_v1.log
grep -q "EQUITY_PRE_SIGNAL_GUARD_PATCH_PLAN_SUMMARY" /tmp/equity_pre_signal_guard_patch_plan_v1.log
grep -q "hits_total=" /tmp/equity_pre_signal_guard_patch_plan_v1.log
grep -q "br_volatility_reason_hits=" /tmp/equity_pre_signal_guard_patch_plan_v1.log
grep -q "VERDICT=" /tmp/equity_pre_signal_guard_patch_plan_v1.log
grep -q "db_update=0" /tmp/equity_pre_signal_guard_patch_plan_v1.log

echo
echo "=== EQUITY PRE SIGNAL GUARD PATCH PLAN SUMMARY ==="
grep -E "EQUITY_PRE_SIGNAL_GUARD_CODE_HIT|EQUITY_PRE_SIGNAL_GUARD_PATCH_PLAN_ROW|files_with_hits=|hits_total=|br_volatility_reason_hits=|equity_strategy_hits=|guard_table_hits=|VERDICT=" \
  /tmp/equity_pre_signal_guard_patch_plan_v1.log | head -180

echo TEST_EQUITY_PRE_SIGNAL_GUARD_PATCH_PLAN_V1_OK

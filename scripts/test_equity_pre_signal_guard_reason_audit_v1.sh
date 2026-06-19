#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY PRE SIGNAL GUARD REASON AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_equity_pre_signal_guard_reason_audit_v1.py

PYTHONPATH=src python3 src/scripts/research/build_equity_pre_signal_guard_reason_audit_v1.py \
  | tee /tmp/equity_pre_signal_guard_reason_audit_v1.log

grep -q "EQUITY_PRE_SIGNAL_GUARD_REASON_AUDIT_V1_OK" /tmp/equity_pre_signal_guard_reason_audit_v1.log
grep -q "EQUITY_PRE_SIGNAL_GUARD_REASON_AUDIT_SUMMARY" /tmp/equity_pre_signal_guard_reason_audit_v1.log
grep -q "guard_rows_total=" /tmp/equity_pre_signal_guard_reason_audit_v1.log
grep -q "expected_strategy_block_rows=" /tmp/equity_pre_signal_guard_reason_audit_v1.log
grep -q "VERDICT=" /tmp/equity_pre_signal_guard_reason_audit_v1.log
grep -q "db_update=0" /tmp/equity_pre_signal_guard_reason_audit_v1.log

echo
echo "=== EQUITY PRE SIGNAL GUARD SUMMARY ==="
grep -E "EQUITY_PRE_SIGNAL_GUARD_SCHEMA_ROW|EQUITY_PRE_SIGNAL_GUARD_GROUP_ROW|guard_rows_total=|expected_strategy_block_rows=|br_named_reason_rows=|VERDICT=" \
  /tmp/equity_pre_signal_guard_reason_audit_v1.log | head -160

echo TEST_EQUITY_PRE_SIGNAL_GUARD_REASON_AUDIT_V1_OK

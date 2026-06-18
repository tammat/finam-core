#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY PRE SIGNAL GUARD CALLSITE AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_equity_pre_signal_guard_callsite_audit_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_equity_pre_signal_guard_callsite_audit_v1.py \
  | tee /tmp/equity_pre_signal_guard_callsite_audit_v1.log

grep -q "EQUITY_PRE_SIGNAL_GUARD_CALLSITE_AUDIT_V1_OK" /tmp/equity_pre_signal_guard_callsite_audit_v1.log
grep -q "EQUITY_PRE_SIGNAL_GUARD_CALLSITES" /tmp/equity_pre_signal_guard_callsite_audit_v1.log
grep -q "EQUITY_PRE_SIGNAL_GUARD_CALLSITE_AUDIT_SUMMARY" /tmp/equity_pre_signal_guard_callsite_audit_v1.log
grep -q "db_update=0" /tmp/equity_pre_signal_guard_callsite_audit_v1.log
grep -q "file_update=0" /tmp/equity_pre_signal_guard_callsite_audit_v1.log
grep -q "VERDICT=" /tmp/equity_pre_signal_guard_callsite_audit_v1.log

echo
echo "=== EQUITY PRE SIGNAL GUARD CALLSITE AUDIT SUMMARY ==="
grep -E "EQUITY_PRE_SIGNAL_GUARD_CALLSITE lineno=|callsites_total=|patched_calls=|legacy_calls=|unclear_calls=|unresolved_legacy=|VERDICT=" \
  /tmp/equity_pre_signal_guard_callsite_audit_v1.log

echo TEST_EQUITY_PRE_SIGNAL_GUARD_CALLSITE_AUDIT_V1_OK

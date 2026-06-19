#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY GUARD THRESHOLD AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_equity_guard_threshold_audit_v1.py

PYTHONPATH=src python3 src/scripts/research/build_equity_guard_threshold_audit_v1.py \
  | tee /tmp/equity_guard_threshold_audit_v1.log

grep -q "EQUITY_GUARD_THRESHOLD_AUDIT_V1_OK" /tmp/equity_guard_threshold_audit_v1.log
grep -q "EQUITY_GUARD_THRESHOLD_AUDIT_SUMMARY" /tmp/equity_guard_threshold_audit_v1.log
grep -q "guard_rows_total=" /tmp/equity_guard_threshold_audit_v1.log
grep -q "br_volatility_too_low_rows=" /tmp/equity_guard_threshold_audit_v1.log
grep -q "avg_atr_pct=" /tmp/equity_guard_threshold_audit_v1.log
grep -q "avg_threshold=" /tmp/equity_guard_threshold_audit_v1.log
grep -q "VERDICT=" /tmp/equity_guard_threshold_audit_v1.log
grep -q "db_update=0" /tmp/equity_guard_threshold_audit_v1.log

echo
echo "=== EQUITY GUARD THRESHOLD SUMMARY ==="
grep -E "EQUITY_GUARD_THRESHOLD_REASON_ROW|EQUITY_GUARD_THRESHOLD_SAMPLE_ROW|guard_rows_total=|br_volatility_too_low_rows=|compression_watch_active_rows=|avg_atr_pct=|avg_threshold=|VERDICT=" \
  /tmp/equity_guard_threshold_audit_v1.log | head -160

echo TEST_EQUITY_GUARD_THRESHOLD_AUDIT_V1_OK

#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY RUNTIME DISPATCH CHURN AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_equity_runtime_dispatch_churn_audit_v1.py

PYTHONPATH=src \
ACTIVE_SINCE_MSK="${ACTIVE_SINCE_MSK:-2026-06-19 09:13:38}" \
ACTIVE_SINCE_UTC="${ACTIVE_SINCE_UTC:-2026-06-19 06:13:38+00}" \
python3 src/scripts/research/build_equity_runtime_dispatch_churn_audit_v1.py \
  | tee /tmp/equity_runtime_dispatch_churn_audit_v1.log

grep -q "EQUITY_RUNTIME_DISPATCH_CHURN_AUDIT_V1_OK" /tmp/equity_runtime_dispatch_churn_audit_v1.log
grep -q "EQUITY_RUNTIME_DISPATCH_CHURN_AUDIT_SUMMARY" /tmp/equity_runtime_dispatch_churn_audit_v1.log
grep -q "source_ok=" /tmp/equity_runtime_dispatch_churn_audit_v1.log
grep -q "runtime_created_total=" /tmp/equity_runtime_dispatch_churn_audit_v1.log
grep -q "mtf_closed_logs=" /tmp/equity_runtime_dispatch_churn_audit_v1.log
grep -q "equity_route_logs=" /tmp/equity_runtime_dispatch_churn_audit_v1.log
grep -q "VERDICT=" /tmp/equity_runtime_dispatch_churn_audit_v1.log
grep -q "db_update=0" /tmp/equity_runtime_dispatch_churn_audit_v1.log

echo
echo "=== EQUITY RUNTIME DISPATCH CHURN SUMMARY ==="
grep -E "SOURCE_HAS_|EQUITY_RUNTIME_DISPATCH_JOURNAL_ROW|EQUITY_RUNTIME_STRATEGY_CREATED_ROW|EQUITY_RUNTIME_ACTIVE_EQUITY_ROW|EQUITY_RUNTIME_FRESH_BAR_ROW|source_ok=|runtime_created_total=|mtf_closed_logs=|equity_route_logs=|bars_after_restart_total=|VERDICT=" \
  /tmp/equity_runtime_dispatch_churn_audit_v1.log | head -260

echo TEST_EQUITY_RUNTIME_DISPATCH_CHURN_AUDIT_V1_OK

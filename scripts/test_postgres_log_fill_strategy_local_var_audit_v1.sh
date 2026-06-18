#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST POSTGRES LOG FILL STRATEGY LOCAL VAR AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_postgres_log_fill_strategy_local_var_audit_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_postgres_log_fill_strategy_local_var_audit_v1.py \
  | tee /tmp/postgres_log_fill_strategy_local_var_audit_v1.log

grep -q "POSTGRES_LOG_FILL_STRATEGY_LOCAL_VAR_AUDIT_V1_OK" /tmp/postgres_log_fill_strategy_local_var_audit_v1.log
grep -q "POSTGRES_LOG_FILL_STRATEGY_AUDIT_SUMMARY" /tmp/postgres_log_fill_strategy_local_var_audit_v1.log
grep -q "VERDICT=" /tmp/postgres_log_fill_strategy_local_var_audit_v1.log
grep -q "db_update=0" /tmp/postgres_log_fill_strategy_local_var_audit_v1.log

echo
echo "=== POSTGRES LOG FILL STRATEGY LOCAL VAR AUDIT SUMMARY ==="
grep -E "POSTGRES_LOG_FILL_STRATEGY_AUDIT_HIT|has_error_log=|has_strategy_setdefault=|VERDICT=" \
  /tmp/postgres_log_fill_strategy_local_var_audit_v1.log | head -160

echo TEST_POSTGRES_LOG_FILL_STRATEGY_LOCAL_VAR_AUDIT_V1_OK

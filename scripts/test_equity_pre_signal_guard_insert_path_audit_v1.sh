#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY PRE SIGNAL GUARD INSERT PATH AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_equity_pre_signal_guard_insert_path_audit_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_equity_pre_signal_guard_insert_path_audit_v1.py \
  | tee /tmp/equity_pre_signal_guard_insert_path_audit_v1.log

grep -q "EQUITY_PRE_SIGNAL_GUARD_INSERT_PATH_AUDIT_V1_OK" /tmp/equity_pre_signal_guard_insert_path_audit_v1.log
grep -q "EQUITY_PRE_SIGNAL_GUARD_INSERT_PATH_FILES" /tmp/equity_pre_signal_guard_insert_path_audit_v1.log
grep -q "EQUITY_PRE_SIGNAL_GUARD_SAVE_FUNCTIONS" /tmp/equity_pre_signal_guard_insert_path_audit_v1.log
grep -q "EQUITY_PRE_SIGNAL_GUARD_INSERT_PATH_AUDIT_SUMMARY" /tmp/equity_pre_signal_guard_insert_path_audit_v1.log
grep -q "db_update=0" /tmp/equity_pre_signal_guard_insert_path_audit_v1.log
grep -q "file_update=0" /tmp/equity_pre_signal_guard_insert_path_audit_v1.log
grep -q "VERDICT=" /tmp/equity_pre_signal_guard_insert_path_audit_v1.log

echo
echo "=== EQUITY PRE SIGNAL GUARD INSERT PATH AUDIT SUMMARY ==="
grep -E "save_exists=|save_mentions_strategy=|save_has_insert=|save_mentions_default_strategy=|save_mentions_symbol_map=|save_uses_payload_strategy=|direct_table_writes_in_pipeline=|likely_save_override=|VERDICT=" \
  /tmp/equity_pre_signal_guard_insert_path_audit_v1.log

echo TEST_EQUITY_PRE_SIGNAL_GUARD_INSERT_PATH_AUDIT_V1_OK

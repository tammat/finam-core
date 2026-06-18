#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST USDRUB RUNTIME BLOCK CALLSITE AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_usdrub_runtime_block_callsite_audit_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_usdrub_runtime_block_callsite_audit_v1.py \
  | tee /tmp/usdrub_runtime_block_callsite_audit_v1.log

grep -q "USDRUB_RUNTIME_BLOCK_CALLSITE_AUDIT_V1_OK" /tmp/usdrub_runtime_block_callsite_audit_v1.log
grep -q "USDRUB_CALLSITE_AUDIT_SUMMARY" /tmp/usdrub_runtime_block_callsite_audit_v1.log
grep -q "USDRUBF_PAPER_ACCUMULATION_BYPASS" /tmp/usdrub_runtime_block_callsite_audit_v1.log
grep -q "VERDICT=" /tmp/usdrub_runtime_block_callsite_audit_v1.log
grep -q "db_update=0" /tmp/usdrub_runtime_block_callsite_audit_v1.log

echo
echo "=== USDRUB CALLSITE AUDIT SUMMARY ==="
grep -E "helper_present=|generic_guard_present=|bypass_present=|usd_gate_present=|VERDICT=" \
  /tmp/usdrub_runtime_block_callsite_audit_v1.log

echo TEST_USDRUB_RUNTIME_BLOCK_CALLSITE_AUDIT_V1_OK

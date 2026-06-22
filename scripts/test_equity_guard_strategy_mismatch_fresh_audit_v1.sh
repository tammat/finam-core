#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EQUITY_GUARD_STRATEGY_MISMATCH_FRESH_AUDIT_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_equity_guard_strategy_mismatch_fresh_audit_v1.py

python3 \
  src/scripts/research/build_equity_guard_strategy_mismatch_fresh_audit_v1.py \
  | tee /tmp/equity_guard_strategy_mismatch_fresh_audit_v1.log

grep -q "FRESH_SUMMARY" \
  /tmp/equity_guard_strategy_mismatch_fresh_audit_v1.log

grep -q "VERDICT=" \
  /tmp/equity_guard_strategy_mismatch_fresh_audit_v1.log

echo "TEST_EQUITY_GUARD_STRATEGY_MISMATCH_FRESH_AUDIT_V1_OK"

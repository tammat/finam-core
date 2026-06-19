#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY STRATEGY METHOD SIGNATURE AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_equity_strategy_method_signature_audit_v1.py

PYTHONPATH=src python3 src/scripts/research/build_equity_strategy_method_signature_audit_v1.py \
  | tee /tmp/equity_strategy_method_signature_audit_v1.log

grep -q "EQUITY_STRATEGY_METHOD_SIGNATURE_AUDIT_V1_OK" /tmp/equity_strategy_method_signature_audit_v1.log
grep -q "EQUITY_STRATEGY_METHOD_SIGNATURE_AUDIT_SUMMARY" /tmp/equity_strategy_method_signature_audit_v1.log
grep -q "method_rows=" /tmp/equity_strategy_method_signature_audit_v1.log
grep -q "target_method_rows=" /tmp/equity_strategy_method_signature_audit_v1.log
grep -q "pipeline_dispatch_hits=" /tmp/equity_strategy_method_signature_audit_v1.log
grep -q "VERDICT=" /tmp/equity_strategy_method_signature_audit_v1.log
grep -q "db_update=0" /tmp/equity_strategy_method_signature_audit_v1.log

echo
echo "=== EQUITY STRATEGY METHOD SIGNATURE SUMMARY ==="
grep -E "EQUITY_METHOD_ROW|EQUITY_PIPELINE_DISPATCH_HIT|method_rows=|target_method_rows=|pipeline_dispatch_hits=|VERDICT=" \
  /tmp/equity_strategy_method_signature_audit_v1.log | head -220

echo TEST_EQUITY_STRATEGY_METHOD_SIGNATURE_AUDIT_V1_OK

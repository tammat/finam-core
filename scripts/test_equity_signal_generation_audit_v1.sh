#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EQUITY_SIGNAL_GENERATION_AUDIT_V1 ==="

python3 -m py_compile src/scripts/research/build_equity_signal_generation_audit_v1.py

python3 src/scripts/research/build_equity_signal_generation_audit_v1.py \
  | tee /tmp/equity_signal_generation_audit_v1.log

grep -q "EQUITY_SIGNAL_GENERATION_SUMMARY" /tmp/equity_signal_generation_audit_v1.log
grep -q "decision=" /tmp/equity_signal_generation_audit_v1.log
grep -q "VERDICT=EQUITY_SIGNAL_GENERATION_AUDIT_READY" /tmp/equity_signal_generation_audit_v1.log

echo "VERDICT=EQUITY_SIGNAL_GENERATION_AUDIT_TEST_OK"
echo "TEST_EQUITY_SIGNAL_GENERATION_AUDIT_V1_OK"

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_br_runtime_side_bias_audit_v1.py

python3 src/scripts/analytics/build_br_runtime_side_bias_audit_v1.py \
  | tee /tmp/br_runtime_side_bias_audit_v1.log

grep -q "BR RUNTIME SIDE BIAS AUDIT V1" \
  /tmp/br_runtime_side_bias_audit_v1.log

grep -q "CLOSED_TRADE_SIDE_ROWS" \
  /tmp/br_runtime_side_bias_audit_v1.log

grep -q "AUDIT_SUMMARY" \
  /tmp/br_runtime_side_bias_audit_v1.log

grep -q "BR_RUNTIME_SIDE_BIAS_AUDIT_V1_OK" \
  /tmp/br_runtime_side_bias_audit_v1.log

echo "TEST_BR_RUNTIME_SIDE_BIAS_AUDIT_V1_OK"

#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST NGQ6 AFTER RISK EXEC BLOCK AUDIT V1 ==="

python3 -m py_compile src/scripts/research/build_ngq6_after_risk_exec_block_audit_v1.py

python3 src/scripts/research/build_ngq6_after_risk_exec_block_audit_v1.py \
  --since "60 minutes ago" \
  --window "60 minutes" \
  | tee /tmp/ngq6_after_risk_exec_block_audit_v1.log

grep -q "NGQ6_AFTER_RISK_EXEC_BLOCK_AUDIT_V1_OK" /tmp/ngq6_after_risk_exec_block_audit_v1.log
grep -q "VERDICT=" /tmp/ngq6_after_risk_exec_block_audit_v1.log
grep -q "runtime_allow=0" /tmp/ngq6_after_risk_exec_block_audit_v1.log
grep -q "execution_enabled=0" /tmp/ngq6_after_risk_exec_block_audit_v1.log

echo TEST_NGQ6_AFTER_RISK_EXEC_BLOCK_AUDIT_V1_OK

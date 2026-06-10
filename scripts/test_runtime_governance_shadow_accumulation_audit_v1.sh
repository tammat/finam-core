#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_runtime_governance_shadow_accumulation_audit_v1.py

python3 \
  src/scripts/analytics/build_runtime_governance_shadow_accumulation_audit_v1.py \
  | tee /tmp/runtime_governance_shadow_accumulation_audit_v1.log

grep -q "RUNTIME GOVERNANCE SHADOW ACCUMULATION AUDIT V1" \
  /tmp/runtime_governance_shadow_accumulation_audit_v1.log

grep -q "AUDIT_SUMMARY" \
  /tmp/runtime_governance_shadow_accumulation_audit_v1.log

grep -q "runtime_allow_rows=0" \
  /tmp/runtime_governance_shadow_accumulation_audit_v1.log

grep -q "AUDIT_VERDICT=PASS" \
  /tmp/runtime_governance_shadow_accumulation_audit_v1.log

grep -q "RUNTIME_GOVERNANCE_SHADOW_ACCUMULATION_AUDIT_V1_OK" \
  /tmp/runtime_governance_shadow_accumulation_audit_v1.log

echo TEST_RUNTIME_GOVERNANCE_SHADOW_ACCUMULATION_AUDIT_V1_OK

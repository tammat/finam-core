#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_runtime_shadow_validation_gold_autorun_audit_v1.py

python3 \
  src/scripts/research/build_runtime_shadow_validation_gold_autorun_audit_v1.py \
  | tee /tmp/runtime_shadow_validation_gold_autorun_audit_v1.log

grep -q "RUNTIME SHADOW VALIDATION GOLD AUTORUN AUDIT V1" \
  /tmp/runtime_shadow_validation_gold_autorun_audit_v1.log

grep -q "service_ok=1" \
  /tmp/runtime_shadow_validation_gold_autorun_audit_v1.log

grep -q "timer_ok=1" \
  /tmp/runtime_shadow_validation_gold_autorun_audit_v1.log

grep -q "forbidden_hits=0" \
  /tmp/runtime_shadow_validation_gold_autorun_audit_v1.log

grep -q "timer_enabled=enabled" \
  /tmp/runtime_shadow_validation_gold_autorun_audit_v1.log

grep -q "timer_active=active" \
  /tmp/runtime_shadow_validation_gold_autorun_audit_v1.log

grep -q "runtime_allow=0" \
  /tmp/runtime_shadow_validation_gold_autorun_audit_v1.log

grep -q "execution_enabled=0" \
  /tmp/runtime_shadow_validation_gold_autorun_audit_v1.log

grep -q "AUDIT_VERDICT=PASS" \
  /tmp/runtime_shadow_validation_gold_autorun_audit_v1.log

grep -q "RUNTIME_SHADOW_VALIDATION_GOLD_AUTORUN_AUDIT_V1_OK" \
  /tmp/runtime_shadow_validation_gold_autorun_audit_v1.log

echo TEST_RUNTIME_SHADOW_VALIDATION_GOLD_AUTORUN_AUDIT_V1_OK

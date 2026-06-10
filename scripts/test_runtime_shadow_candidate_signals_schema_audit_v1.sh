#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_runtime_shadow_candidate_signals_schema_audit_v1.py

python3 \
  src/scripts/analytics/build_runtime_shadow_candidate_signals_schema_audit_v1.py \
  | tee /tmp/runtime_shadow_candidate_signals_schema_audit_v1.log

grep -q "RUNTIME SHADOW CANDIDATE SIGNALS SCHEMA AUDIT V1" \
  /tmp/runtime_shadow_candidate_signals_schema_audit_v1.log

grep -q "table_exists=1" \
  /tmp/runtime_shadow_candidate_signals_schema_audit_v1.log

grep -q "runtime_allow_ok=1" \
  /tmp/runtime_shadow_candidate_signals_schema_audit_v1.log

grep -q "execution_enabled_ok=1" \
  /tmp/runtime_shadow_candidate_signals_schema_audit_v1.log

grep -q "AUDIT_VERDICT=PASS" \
  /tmp/runtime_shadow_candidate_signals_schema_audit_v1.log

grep -q "RUNTIME_SHADOW_CANDIDATE_SIGNALS_SCHEMA_AUDIT_V1_OK" \
  /tmp/runtime_shadow_candidate_signals_schema_audit_v1.log

echo TEST_RUNTIME_SHADOW_CANDIDATE_SIGNALS_SCHEMA_AUDIT_V1_OK

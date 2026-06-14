#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/runtime/build_shadow_runtime_price_scale_audit_v1.py

python3 src/scripts/runtime/build_shadow_runtime_price_scale_audit_v1.py \
  | tee /tmp/shadow_runtime_price_scale_audit_v1.log

grep -q "SHADOW RUNTIME PRICE SCALE AUDIT V1" /tmp/shadow_runtime_price_scale_audit_v1.log
grep -q "PRICE_SCALE_AUDIT_ROW" /tmp/shadow_runtime_price_scale_audit_v1.log
grep -q "LKOH@MISX" /tmp/shadow_runtime_price_scale_audit_v1.log
grep -q "audit_status=" /tmp/shadow_runtime_price_scale_audit_v1.log
grep -q "runtime_allow=0" /tmp/shadow_runtime_price_scale_audit_v1.log
grep -q "execution_enabled=0" /tmp/shadow_runtime_price_scale_audit_v1.log
grep -q "SHADOW_RUNTIME_PRICE_SCALE_AUDIT_V1_OK" /tmp/shadow_runtime_price_scale_audit_v1.log

echo TEST_SHADOW_RUNTIME_PRICE_SCALE_AUDIT_V1_OK

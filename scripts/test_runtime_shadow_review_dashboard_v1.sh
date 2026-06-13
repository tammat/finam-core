#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/runtime/build_runtime_shadow_review_dashboard_v1.py

python3 src/scripts/runtime/build_runtime_shadow_review_dashboard_v1.py \
  | tee /tmp/runtime_shadow_review_dashboard_v1.log

grep -q "RUNTIME SHADOW REVIEW DASHBOARD V1" /tmp/runtime_shadow_review_dashboard_v1.log
grep -q "GDU6@RTSX" /tmp/runtime_shadow_review_dashboard_v1.log
grep -q "LKOH@MISX" /tmp/runtime_shadow_review_dashboard_v1.log
grep -q "READY_FOR_SHADOW_RUNTIME" /tmp/runtime_shadow_review_dashboard_v1.log
grep -q "runtime_allow=0" /tmp/runtime_shadow_review_dashboard_v1.log
grep -q "execution_enabled=0" /tmp/runtime_shadow_review_dashboard_v1.log
grep -q "RUNTIME_SHADOW_REVIEW_DASHBOARD_V1_OK" /tmp/runtime_shadow_review_dashboard_v1.log

echo TEST_RUNTIME_SHADOW_REVIEW_DASHBOARD_V1_OK

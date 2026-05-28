#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_ROLLOUT_ENABLE_PLAN_V1_START"

python -m py_compile \
  src/scripts/analytics/build_runtime_rollout_enable_plan_v1.py

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_runtime_rollout_enable_plan_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "RUNTIME_ROLLOUT_ENABLE_PLAN_V1" "$TMP_LOG"
grep -q "READY_FOR_ENABLE" "$TMP_LOG"
grep -q "phase=5" "$TMP_LOG"
grep -q "strict_mode=enabled" "$TMP_LOG"
grep -q "decay_monitor=enabled" "$TMP_LOG"

echo "TEST_RUNTIME_ROLLOUT_ENABLE_PLAN_V1_OK"

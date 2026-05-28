#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_ROLLOUT_PHASE1_SHADOW_V1_START"

python -m py_compile \
  src/scripts/analytics/build_runtime_rollout_phase1_shadow_v1.py

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_runtime_rollout_phase1_shadow_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "RUNTIME_ROLLOUT_PHASE1_SHADOW_V1" "$TMP_LOG"
grep -q "PHASE1_READY" "$TMP_LOG"
grep -q "mode=paper_shadow" "$TMP_LOG"
grep -q "execution_blocking=false" "$TMP_LOG"
grep -q "shadow_runtime=true" "$TMP_LOG"

echo "TEST_RUNTIME_ROLLOUT_PHASE1_SHADOW_V1_OK"

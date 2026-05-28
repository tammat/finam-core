#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_POSITION_SEED_PLAN_V1_START"

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_runtime_position_seed_plan_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "RUNTIME_POSITION_SEED_PLAN_V1" "$TMP_LOG"
grep -q "RUNTIME_POSITION_SEED_PLAN_SUMMARY" "$TMP_LOG"
grep -q "RUNTIME_POSITION_SEED_PLAN_V1_OK" "$TMP_LOG"
grep -q "mode=DRY_RUN" "$TMP_LOG"

echo "TEST_RUNTIME_POSITION_SEED_PLAN_V1_OK"

#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_PHASE2_SOFT_BLOCK_LIVE_OBSERVATION_V1_START"

python -m py_compile \
  src/scripts/analytics/build_phase2_soft_block_live_observation_v1.py

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_phase2_soft_block_live_observation_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "PHASE2_SOFT_BLOCK_LIVE_OBSERVATION_V1" "$TMP_LOG"
grep -q "PHASE2_SOFT_BLOCK_LIVE_OBSERVATION_STATUS" "$TMP_LOG"
grep -q "PHASE2_SOFT_BLOCK_LIVE_OBSERVATION_V1_OK" "$TMP_LOG"

echo "TEST_PHASE2_SOFT_BLOCK_LIVE_OBSERVATION_V1_OK"

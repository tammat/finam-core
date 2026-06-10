#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_runtime_shadow_candidate_seed_v1.py

python3 \
  src/scripts/analytics/build_runtime_shadow_candidate_seed_v1.py \
  | tee /tmp/runtime_shadow_candidate_seed_v1.log

grep -q "RUNTIME SHADOW CANDIDATE SEED V1" \
  /tmp/runtime_shadow_candidate_seed_v1.log

grep -q "symbol=USDRUBF@RTSX" \
  /tmp/runtime_shadow_candidate_seed_v1.log

grep -q "symbol=LKOH@MISX" \
  /tmp/runtime_shadow_candidate_seed_v1.log

grep -q "runtime_allow=0" \
  /tmp/runtime_shadow_candidate_seed_v1.log

grep -q "execution_enabled=0" \
  /tmp/runtime_shadow_candidate_seed_v1.log

grep -q "RUNTIME_SHADOW_CANDIDATE_SEED_V1_OK" \
  /tmp/runtime_shadow_candidate_seed_v1.log

echo TEST_RUNTIME_SHADOW_CANDIDATE_SEED_V1_OK

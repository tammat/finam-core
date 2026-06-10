#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_shadow_candidate_activation_plan_v1.py

python3 \
  src/scripts/analytics/build_shadow_candidate_activation_plan_v1.py \
  | tee /tmp/shadow_candidate_activation_plan_v1.log

grep -q "SHADOW CANDIDATE ACTIVATION PLAN V1" \
  /tmp/shadow_candidate_activation_plan_v1.log

grep -q "symbol=USDRUBF@RTSX" \
  /tmp/shadow_candidate_activation_plan_v1.log

grep -q "symbol=LKOH@MISX" \
  /tmp/shadow_candidate_activation_plan_v1.log

grep -q "runtime_allow=0" \
  /tmp/shadow_candidate_activation_plan_v1.log

grep -q "SHADOW_CANDIDATE_ACTIVATION_PLAN_V1_OK" \
  /tmp/shadow_candidate_activation_plan_v1.log

echo TEST_SHADOW_CANDIDATE_ACTIVATION_PLAN_V1_OK

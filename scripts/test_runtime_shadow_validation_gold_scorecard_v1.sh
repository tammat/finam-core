#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src
export GOLD_SYMBOL=GDU6@RTSX

python3 -m py_compile \
  src/scripts/research/build_runtime_shadow_validation_gold_scorecard_v1.py

python3 \
  src/scripts/research/build_runtime_shadow_validation_gold_scorecard_v1.py \
  | tee /tmp/runtime_shadow_validation_gold_scorecard_v1.log

grep -q "RUNTIME SHADOW VALIDATION GOLD SCORECARD V1" \
  /tmp/runtime_shadow_validation_gold_scorecard_v1.log

grep -q "symbol=GDU6@RTSX" \
  /tmp/runtime_shadow_validation_gold_scorecard_v1.log

grep -q "runtime_allow=0" \
  /tmp/runtime_shadow_validation_gold_scorecard_v1.log

grep -q "execution_enabled=0" \
  /tmp/runtime_shadow_validation_gold_scorecard_v1.log

grep -q "RUNTIME_SHADOW_VALIDATION_GOLD_SCORECARD_V1_OK" \
  /tmp/runtime_shadow_validation_gold_scorecard_v1.log

echo TEST_RUNTIME_SHADOW_VALIDATION_GOLD_SCORECARD_V1_OK

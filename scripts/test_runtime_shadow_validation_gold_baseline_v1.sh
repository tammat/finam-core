#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_runtime_shadow_validation_gold_baseline_v1.py

python3 \
  src/scripts/analytics/build_runtime_shadow_validation_gold_baseline_v1.py \
  | tee /tmp/runtime_shadow_validation_gold_baseline_v1.log

grep -q "RUNTIME SHADOW VALIDATION GOLD BASELINE V1" \
  /tmp/runtime_shadow_validation_gold_baseline_v1.log

grep -q "symbol=GDU6@RTSX" \
  /tmp/runtime_shadow_validation_gold_baseline_v1.log

grep -q "RUNTIME_SHADOW_VALIDATION_GOLD_BASELINE_V1_OK" \
  /tmp/runtime_shadow_validation_gold_baseline_v1.log

echo TEST_RUNTIME_SHADOW_VALIDATION_GOLD_BASELINE_V1_OK

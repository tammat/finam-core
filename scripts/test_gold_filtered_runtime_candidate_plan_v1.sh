#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_FILTERED_RUNTIME_CANDIDATE_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_gold_filtered_runtime_candidate_plan_v1.py

src/scripts/research/build_gold_filtered_runtime_candidate_plan_v1.py \
  | tee /tmp/gold_filtered_runtime_candidate_plan_v1.out

grep -q "GOLD_FILTERED_RUNTIME_CANDIDATE_PLAN_V1" \
  /tmp/gold_filtered_runtime_candidate_plan_v1.out

grep -q "VERDICT=GOLD_FILTERED_RUNTIME_CANDIDATE_PLAN_READY" \
  /tmp/gold_filtered_runtime_candidate_plan_v1.out

echo "TEST_GOLD_FILTERED_RUNTIME_CANDIDATE_PLAN_V1_OK"

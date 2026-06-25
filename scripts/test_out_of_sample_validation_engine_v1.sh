#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_OUT_OF_SAMPLE_VALIDATION_ENGINE_V1 ==="

src/scripts/research/build_out_of_sample_validation_engine_v1.py \
  --candidate-id MSC-000001 \
  | tee /tmp/oos_validation_engine_v1.out

grep -q "OUT_OF_SAMPLE_VALIDATION_ENGINE_V1" /tmp/oos_validation_engine_v1.out
grep -q "candidate_id=MSC-000001" /tmp/oos_validation_engine_v1.out
grep -q "runtime_changed=0" /tmp/oos_validation_engine_v1.out
grep -q "micro_live_allowed=0" /tmp/oos_validation_engine_v1.out
grep -Eq "decision=(PASS_TO_SHADOW|UNDER_REVIEW|REJECT)" /tmp/oos_validation_engine_v1.out
grep -q "VERDICT=" /tmp/oos_validation_engine_v1.out

echo "TEST_OUT_OF_SAMPLE_VALIDATION_ENGINE_V1_OK"

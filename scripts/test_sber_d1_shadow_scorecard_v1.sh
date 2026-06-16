#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_sber_d1_shadow_scorecard_v1.py

python3 \
  src/scripts/research/build_sber_d1_shadow_scorecard_v1.py \
  | tee /tmp/sber_shadow_scorecard_v1.log

grep -q "SBER D1 SHADOW SCORECARD V1" \
  /tmp/sber_shadow_scorecard_v1.log

grep -q "runtime_allow=0" \
  /tmp/sber_shadow_scorecard_v1.log

grep -q "execution_enabled=0" \
  /tmp/sber_shadow_scorecard_v1.log

grep -q "SBER_D1_SHADOW_SCORECARD_V1_OK" \
  /tmp/sber_shadow_scorecard_v1.log

echo TEST_SBER_D1_SHADOW_SCORECARD_V1_OK

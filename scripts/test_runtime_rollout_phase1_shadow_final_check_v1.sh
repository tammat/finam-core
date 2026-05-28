#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_ROLLOUT_PHASE1_SHADOW_FINAL_CHECK_V1_START"

python -m py_compile \
  src/scripts/analytics/build_runtime_rollout_phase1_shadow_final_check_v1.py

python src/scripts/analytics/build_runtime_rollout_phase1_shadow_final_check_v1.py

grep -q "PHASE1_SHADOW_FINAL_READY" <(
  python src/scripts/analytics/build_runtime_rollout_phase1_shadow_final_check_v1.py
)

echo "TEST_RUNTIME_ROLLOUT_PHASE1_SHADOW_FINAL_CHECK_V1_OK"

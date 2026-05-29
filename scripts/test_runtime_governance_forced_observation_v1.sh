#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_GOVERNANCE_FORCED_OBSERVATION_V1_START"

python -m py_compile \
  src/scripts/analytics/build_runtime_governance_forced_observation_v1.py \
  src/finam_core/execution/runtime_edge_governance_soft_block_v1.py \
  src/finam_core/execution/runtime_governance_live_accumulation_v1.py

python src/scripts/analytics/build_runtime_governance_forced_observation_v1.py \
  --symbol BRN6@RTSX \
  --runs 1 \
  --sides BUY,SELL

echo "TEST_RUNTIME_GOVERNANCE_FORCED_OBSERVATION_V1_OK"

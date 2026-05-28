#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_REAL_OBSERVATION_V1_START"

python -m py_compile \
  src/scripts/analytics/build_runtime_governance_live_accumulation_real_observation_v1.py \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/execution/runtime_governance_live_accumulation_v1.py

echo "BEFORE_REAL_PIPELINE_OBSERVATION"
python src/scripts/analytics/build_runtime_governance_live_accumulation_real_observation_v1.py \
  --window-minutes 120

echo "RUN_SHORT_PAPER_PIPELINE_FOR_REAL_OBSERVATION"

set +e
timeout 90s env \
  PYTHONPATH=src \
  EXECUTION_MODE=paper \
  RISK_SOFT=1 \
  EXIT_ON_FILL=1 \
  python src/scripts/run_market_pipeline.py \
    --symbol BRN6@RTSX \
    --strategy once_buy \
    --run-secs 45 \
    --starting-cash 100000
PIPE_RC=$?
set -e

echo "PIPELINE_EXIT_CODE=${PIPE_RC}"

echo "AFTER_REAL_PIPELINE_OBSERVATION"
python src/scripts/analytics/build_runtime_governance_live_accumulation_real_observation_v1.py \
  --window-minutes 120

echo "TEST_RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_REAL_OBSERVATION_V1_OK"

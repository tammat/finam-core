#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_GOVERNANCE_OBSERVATION_SESSION_BYPASS_V1_START"

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/scripts/run_market_pipeline.py

grep -q "RUNTIME_GOVERNANCE_OBSERVATION_BYPASS_SESSION_PREOPEN" \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "PIPE_SESSION_BLOCK_BYPASS_OBSERVATION" \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "RUNTIME_GOVERNANCE_OBSERVATION_BYPASS_SESSION_PREOPEN=1" \
  scripts/runtime_governance_population_runner_v1.sh

echo "TEST_RUNTIME_GOVERNANCE_OBSERVATION_SESSION_BYPASS_V1_OK"

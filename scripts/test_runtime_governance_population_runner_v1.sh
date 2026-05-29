#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_GOVERNANCE_POPULATION_RUNNER_V1_START"

bash -n scripts/runtime_governance_population_runner_v1.sh

python -m py_compile \
  src/scripts/analytics/build_runtime_governance_population_status_v1.py \
  src/scripts/analytics/build_runtime_governance_effectiveness_v1.py \
  src/scripts/run_market_pipeline.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "RUNTIME_GOVERNANCE_POPULATION_RUNNER_V1_START" \
  scripts/runtime_governance_population_runner_v1.sh

grep -q "RUNTIME_GOVERNANCE_POPULATION_RUNNER_V1_OK" \
  scripts/runtime_governance_population_runner_v1.sh

echo "TEST_RUNTIME_GOVERNANCE_POPULATION_RUNNER_V1_OK"

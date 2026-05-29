#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_GOVERNANCE_POPULATION_STATUS_V1_START"

python -m py_compile \
  src/scripts/analytics/build_runtime_governance_population_status_v1.py

python src/scripts/analytics/build_runtime_governance_population_status_v1.py \
  --window-hours 168

echo "TEST_RUNTIME_GOVERNANCE_POPULATION_STATUS_V1_OK"

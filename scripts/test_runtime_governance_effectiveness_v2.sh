#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_GOVERNANCE_EFFECTIVENESS_V2_START"

python -m py_compile \
  src/scripts/analytics/build_runtime_governance_effectiveness_v2.py

python src/scripts/analytics/build_runtime_governance_effectiveness_v2.py \
  --window-hours 168

echo "TEST_RUNTIME_GOVERNANCE_EFFECTIVENESS_V2_OK"

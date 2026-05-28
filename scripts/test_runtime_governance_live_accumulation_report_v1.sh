#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_REPORT_V1_START"

python -m py_compile \
  src/scripts/analytics/build_runtime_governance_live_accumulation_report_v1.py

python src/scripts/analytics/build_runtime_governance_live_accumulation_report_v1.py

echo "TEST_RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_REPORT_V1_OK"

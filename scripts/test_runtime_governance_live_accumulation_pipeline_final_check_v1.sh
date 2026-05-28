#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_PIPELINE_FINAL_CHECK_V1_START"

python -m py_compile \
  src/finam_core/execution/runtime_governance_live_accumulation_v1.py \
  src/finam_core/pipelines/paper_pipeline.py \
  src/scripts/analytics/build_runtime_governance_live_accumulation_pipeline_final_check_v1.py

python src/scripts/analytics/build_runtime_governance_live_accumulation_pipeline_final_check_v1.py

echo "TEST_RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_PIPELINE_FINAL_CHECK_V1_OK"

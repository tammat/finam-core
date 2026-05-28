#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_PHASE2_SOFT_BLOCK_PRODUCTION_STATUS_V1_START"

python -m py_compile \
  src/scripts/analytics/build_phase2_soft_block_production_status_v1.py \
  src/finam_core/execution/runtime_edge_governance_soft_block_v1.py \
  src/finam_core/pipelines/paper_pipeline.py

python src/scripts/analytics/build_phase2_soft_block_production_status_v1.py

echo "TEST_PHASE2_SOFT_BLOCK_PRODUCTION_STATUS_V1_OK"

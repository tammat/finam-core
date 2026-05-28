#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_GOVERNANCE_STAGE_FINAL_CHECK_V1_START"

python -m py_compile \
  src/scripts/analytics/build_runtime_governance_stage_final_check_v1.py \
  src/finam_core/execution/runtime_edge_governance_soft_block_v1.py \
  src/finam_core/pipelines/paper_pipeline.py

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_runtime_governance_stage_final_check_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "RUNTIME_GOVERNANCE_STAGE_FINAL_CHECK_V1" "$TMP_LOG"
grep -q "RUNTIME_GOVERNANCE_STAGE_CHECK_ROW" "$TMP_LOG"
grep -q "RUNTIME_GOVERNANCE_STAGE_FINAL_STATUS" "$TMP_LOG"
grep -q "RUNTIME_GOVERNANCE_STAGE_FINAL_CHECK_V1_OK" "$TMP_LOG"

echo "TEST_RUNTIME_GOVERNANCE_STAGE_FINAL_CHECK_V1_OK"

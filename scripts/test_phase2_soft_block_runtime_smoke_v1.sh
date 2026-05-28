#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_PHASE2_SOFT_BLOCK_RUNTIME_SMOKE_V1_START"

python -m py_compile \
  src/finam_core/execution/runtime_edge_governance_soft_block_v1.py \
  src/finam_core/pipelines/paper_pipeline.py \
  src/scripts/analytics/build_phase2_soft_block_runtime_smoke_v1.py

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_phase2_soft_block_runtime_smoke_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "PHASE2_RUNTIME_SOFT_BLOCK_SMOKE_V1" "$TMP_LOG"
grep -q "PHASE2_RUNTIME_SOFT_BLOCK_ALLOW" "$TMP_LOG"
grep -q "allowed=True" "$TMP_LOG"
grep -q "PHASE2_RUNTIME_SOFT_BLOCK_BLOCK" "$TMP_LOG"
grep -q "allowed=False" "$TMP_LOG"
grep -q "PHASE2_RUNTIME_SOFT_BLOCK_SMOKE_V1_OK" "$TMP_LOG"

echo "TEST_PHASE2_SOFT_BLOCK_RUNTIME_SMOKE_V1_OK"

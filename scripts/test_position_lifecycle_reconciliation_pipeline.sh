#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/position_lifecycle_reconciler.py \
  src/finam_core/execution/position_lifecycle_state_repository.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "PositionLifecycleReconciler" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_POSITION_LIFECYCLE_RECONCILE_CLEAR" src/finam_core/pipelines/paper_pipeline.py
grep -q "ENABLE_POSITION_LIFECYCLE_RECONCILIATION" src/finam_core/pipelines/paper_pipeline.py

echo "OK: position lifecycle reconciliation pipeline wired"

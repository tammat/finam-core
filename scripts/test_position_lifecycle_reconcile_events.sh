#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/position_lifecycle_reconcile_event_repository.py \
  src/finam_core/execution/position_lifecycle_reconciler.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "PositionLifecycleReconcileEventRepository" src/finam_core/pipelines/paper_pipeline.py
grep -q "POSITION_LIFECYCLE_RECONCILE_EVENT_LOG_FAILED" src/finam_core/execution/position_lifecycle_reconcile_event_repository.py

echo "OK: position lifecycle reconcile events configured"

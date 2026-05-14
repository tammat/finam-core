#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/position_lifecycle_self_healer.py \
  src/finam_core/execution/position_lifecycle_state_repository.py \
  src/finam_core/execution/position_lifecycle_reconcile_event_repository.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "PositionLifecycleSelfHealer" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_POSITION_LIFECYCLE_SELF_HEAL_DELETE" src/finam_core/pipelines/paper_pipeline.py
grep -q "ENABLE_POSITION_LIFECYCLE_SELF_HEALING" src/finam_core/pipelines/paper_pipeline.py

echo "OK: position lifecycle self-healing pipeline wired"

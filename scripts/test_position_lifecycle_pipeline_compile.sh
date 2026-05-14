#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/position_lifecycle_state_repository.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "PositionLifecycleStateRepository" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_POSITION_LIFECYCLE_STATE_SAVE_FAILED" src/finam_core/pipelines/paper_pipeline.py
grep -q "_save_position_lifecycle_state" src/finam_core/pipelines/paper_pipeline.py

echo "OK: position lifecycle persistence pipeline compile"

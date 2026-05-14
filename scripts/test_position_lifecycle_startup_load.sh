#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/position_lifecycle_state_repository.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "_load_position_lifecycle_state_for_symbol" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_POSITION_LIFECYCLE_STATE_LOADED" src/finam_core/pipelines/paper_pipeline.py
grep -q "tp1_done=bool" src/finam_core/pipelines/paper_pipeline.py

echo "OK: position lifecycle startup load wired"

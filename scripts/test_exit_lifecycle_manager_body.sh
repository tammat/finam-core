#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/exit_lifecycle_manager.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "def build_exit_intent_if_any" \
  src/finam_core/execution/exit_lifecycle_manager.py

grep -q "PIPE_EXIT_ENGINE" \
  src/finam_core/execution/exit_lifecycle_manager.py

grep -q "p._exit_engine_for_symbol" \
  src/finam_core/execution/exit_lifecycle_manager.py

echo "OK: exit lifecycle body moved into manager"

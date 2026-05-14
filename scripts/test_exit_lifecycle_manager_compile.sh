#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/exit_lifecycle_manager.py \
  src/finam_core/execution/position_lifecycle_service.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "class ExitLifecycleManager" src/finam_core/execution/exit_lifecycle_manager.py
grep -q "ExitLifecycleInput" src/finam_core/pipelines/paper_pipeline.py
grep -q "self.exit_lifecycle_manager = ExitLifecycleManager(self)" src/finam_core/pipelines/paper_pipeline.py
grep -q "exit_lifecycle_manager.build_exit_intent_if_any" src/finam_core/pipelines/paper_pipeline.py

echo "OK: exit lifecycle manager compile"

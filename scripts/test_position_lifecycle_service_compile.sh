#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/position_lifecycle_service.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "PositionLifecycleService" src/finam_core/pipelines/paper_pipeline.py
grep -q "PositionLifecycleInput" src/finam_core/pipelines/paper_pipeline.py
grep -q "on_position_quote" src/finam_core/execution/position_lifecycle_service.py

echo "OK: position lifecycle service compile"

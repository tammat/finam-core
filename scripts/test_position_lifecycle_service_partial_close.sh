#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/position_lifecycle_service.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "PIPE_PARTIAL_CLOSE_DECISION" src/finam_core/execution/position_lifecycle_service.py
grep -q "partial_close_engine.evaluate_long" src/finam_core/execution/position_lifecycle_service.py
grep -q "self._evaluate_partial_close_engine" src/finam_core/execution/position_lifecycle_service.py

echo "OK: partial close moved into position lifecycle service"

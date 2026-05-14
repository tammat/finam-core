#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/position_lifecycle_service.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "PIPE_PROFIT_LOCK_DECISION" src/finam_core/execution/position_lifecycle_service.py
grep -q "profit_lock_engine.evaluate_long" src/finam_core/execution/position_lifecycle_service.py
grep -q "profit_lock_event_repository.log_event" src/finam_core/execution/position_lifecycle_service.py
grep -q "self._evaluate_profit_lock_engine" src/finam_core/execution/position_lifecycle_service.py

echo "OK: profit lock moved into position lifecycle service"

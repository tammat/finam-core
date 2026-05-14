#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/position_lifecycle_service.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "position_lifecycle_service" src/finam_core/execution/position_lifecycle_service.py
grep -q "PIPE_TAKE_PROFIT_DECISION" src/finam_core/execution/position_lifecycle_service.py
grep -q "take_profit_event_repository.log_event" src/finam_core/execution/position_lifecycle_service.py

echo "OK: take profit moved into position lifecycle service"

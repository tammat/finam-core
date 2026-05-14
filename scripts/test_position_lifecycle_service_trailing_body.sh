#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/position_lifecycle_service.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "trailing stop lifecycle перенесён" \
  src/finam_core/execution/position_lifecycle_service.py

grep -q "p.trailing_order_manager.evaluate_long" \
  src/finam_core/execution/position_lifecycle_service.py

grep -q "PIPE_TRAILING_ORDER_DECISION" \
  src/finam_core/execution/position_lifecycle_service.py

! grep -q "p._evaluate_trailing_order_manager" \
  src/finam_core/execution/position_lifecycle_service.py

echo "OK: trailing body moved into position lifecycle service"

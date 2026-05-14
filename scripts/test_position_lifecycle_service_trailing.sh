#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/position_lifecycle_service.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "PIPE_TRAILING_ORDER_ERROR" src/finam_core/execution/position_lifecycle_service.py
grep -q "self._evaluate_trailing_order_manager" src/finam_core/execution/position_lifecycle_service.py
grep -q "trailing lifecycle теперь вызывается через сервис" src/finam_core/execution/position_lifecycle_service.py

echo "OK: trailing lifecycle routed through position lifecycle service"

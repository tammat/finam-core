#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/engine/trading_engine_coordinator.py \
  src/finam_core/execution/execution_gateway.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "ENABLE_ENGINE_COORDINATOR_EXECUTION_ROUTE" in text
assert "coordinator.route_execution(intent, market_state)" in text
assert "PIPE_ENGINE_COORDINATOR_EXECUTION_ROUTE" in text
assert "self._route_order_if_enabled(intent, market_state)" in text
assert "PIPE_EXECUTION_DISPATCH_SKIP reason=route_none" in text

print("OK: engine coordinator execution route flag exists")
PY

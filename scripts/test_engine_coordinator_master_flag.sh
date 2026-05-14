#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export ENABLE_ENGINE_COORDINATOR=1

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/engine/trading_engine_coordinator.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert 'ENABLE_ENGINE_COORDINATOR", "0") == "1"' in text
assert "ENABLE_ENGINE_COORDINATOR_ON_QUOTE" in text
assert "ENABLE_ENGINE_COORDINATOR_RECONCILE" in text
assert "ENABLE_ENGINE_COORDINATOR_EXECUTION_ROUTE" in text
assert "coordinator.on_quote(event)" in text
assert "coordinator.reconcile(" in text
assert "coordinator.route_execution(intent, market_state)" in text

print("OK: engine coordinator master flag")
PY

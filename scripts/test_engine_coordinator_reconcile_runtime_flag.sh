#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/engine/trading_engine_coordinator.py \
  src/finam_core/portfolio/portfolio_reconciliation_layer.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "ENABLE_ENGINE_COORDINATOR_RECONCILE" in text
assert "coordinator.reconcile(" in text
assert "PIPE_ENGINE_COORDINATOR_RECONCILE" in text
assert "context={\"source\": \"restart_recovery\"}" in text
assert "self._refresh_broker_position_hard_gate()" in text

print("OK: engine coordinator reconcile gated runtime path exists")
PY

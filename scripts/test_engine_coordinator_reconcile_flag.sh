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

assert "PortfolioReconciliationLayer" in text
assert "self.portfolio_reconciliation_layer = PortfolioReconciliationLayer(" in text
assert "self.engine_coordinator.portfolio_reconciliation_layer" in text

print("OK: engine coordinator reconciliation layer wiring exists")
PY

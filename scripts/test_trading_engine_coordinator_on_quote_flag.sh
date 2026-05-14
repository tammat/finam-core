#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/engine/trading_engine_coordinator.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "ENABLE_ENGINE_COORDINATOR_ON_QUOTE" in text
assert "coordinator.on_quote(event)" in text
assert "self.pipeline_orchestrator.on_quote" in text
assert "QuoteEventContext(event=event)" in text

print("OK: coordinator on_quote flag wiring exists")
PY

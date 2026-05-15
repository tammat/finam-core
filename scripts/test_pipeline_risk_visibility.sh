#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/risk/risk_router.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

router = Path("src/finam_core/risk/risk_router.py").read_text(encoding="utf-8")
pipeline = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "from finam_core.risk.context_builders import build_risk_context" in router
assert "self.last_context = None" in router
assert "self.last_context = ctx" in router
assert "PIPE_TRADE_LIMIT_ACCOUNTED" in pipeline
assert "PIPE_TRADE_EXEC global=" not in pipeline

print("OK: risk visibility and trade-limit log fixed")
PY

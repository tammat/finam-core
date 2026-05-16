#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

checks = [
    'features["requested_symbol"] = decision.requested_symbol',
    'features["execution_symbol"] = decision.execution_symbol',
    'intent["requested_symbol"] = decision.requested_symbol',
    'intent["symbol"] = decision.execution_symbol',
    'market_state["requested_symbol"] = decision.requested_symbol',
    'market_state["symbol"] = decision.execution_symbol',
    "PIPE_EXECUTION_SYMBOL_RESOLVED",
]

for c in checks:
    assert c in text, c

print("OK: pipeline keeps requested_symbol as metadata and execution_symbol as authoritative symbol")
PY

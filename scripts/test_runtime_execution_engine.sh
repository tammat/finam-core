#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_runtime_execution_engine.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/run_runtime_execution_engine.py").read_text(encoding="utf-8")

checks = [
    "runtime_active_universe",
    "RUNTIME_EXECUTION_ACTIVE_SYMBOLS",
    "RUNTIME_EXECUTION_START",
    "run_market_pipeline.py",
    "ENABLE_RUNTIME_ACTIVE_UNIVERSE_GATE",
    "EXECUTION_MODE",
]

for c in checks:
    assert c in text, c

print("OK: runtime execution engine static check")
PY

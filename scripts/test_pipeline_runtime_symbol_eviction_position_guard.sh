#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

checks = [
    "position_qty = 0.0",
    'positions = getattr(getattr(self, "position_manager", None), "positions", {}) or {}',
    "position = positions.get(stale_symbol)",
    "PIPE_RUNTIME_SYMBOL_EVICT_SKIPPED_OPEN_POSITION",
    "if abs(position_qty) > 0:",
    "continue",
    "PIPE_RUNTIME_SYMBOL_EVICT symbol=",
]

for c in checks:
    assert c in text, c

print("OK: runtime symbol eviction is position-aware")
PY

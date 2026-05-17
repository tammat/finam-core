#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

checks = [
    "ENABLE_RUNTIME_ACTIVE_UNIVERSE_GATE",
    "_runtime_active_universe_allows_paper",
    "runtime_active_universe",
    "PIPE_RUNTIME_ACTIVE_UNIVERSE_OK",
    "gate=runtime_active_universe",
    "_strategy_runtime_control_allows_paper",
]

for c in checks:
    assert c in text, c

gate_pos = text.find("PIPE_RUNTIME_ACTIVE_UNIVERSE_OK")
runtime_pos = text.find("runtime_allowed, runtime_qty, runtime_reason")

assert gate_pos >= 0
assert runtime_pos >= 0
assert gate_pos < runtime_pos

print("OK: paper pipeline runtime active universe gate")
PY

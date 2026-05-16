#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

checks = [
    "PIPE_EXECUTION_SYMBOL_RESOLVED",
    "PIPE_EXECUTION_SYMBOL_UNCHANGED",
    "requested_symbol",
    "execution_symbol",
]

for c in checks:
    assert c in text, c

resolved_pos = text.find("PIPE_EXECUTION_SYMBOL_RESOLVED")
unchanged_pos = text.find("PIPE_EXECUTION_SYMBOL_UNCHANGED")

assert resolved_pos > 0
assert unchanged_pos > 0

print("OK: execution symbol observability")
PY

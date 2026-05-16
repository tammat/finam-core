#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

reload_pos = text.find("_runtime_symbol_reload_if_due(preload_symbols)")
session_pos = text.find("PIPE_SESSION_BLOCK phase")

assert reload_pos != -1
assert session_pos != -1
assert reload_pos < session_pos
assert "PIPE_RUNTIME_SYMBOL_RELOAD_PRE_SESSION_ERROR" in text

print("OK: runtime symbol reload runs before session block")
PY

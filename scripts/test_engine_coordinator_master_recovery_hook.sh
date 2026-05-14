#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/engine/trading_engine_coordinator.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "self._run_restart_recovery_if_needed()" in text
assert "result = coordinator.on_quote(event)" in text
assert text.index("self._run_restart_recovery_if_needed()") < text.index("result = coordinator.on_quote(event)")

print("OK: coordinator quote path preserves restart recovery")
PY

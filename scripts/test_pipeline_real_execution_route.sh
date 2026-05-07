#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text()

assert "self.real_execution = RealExecutionEngine" in text
assert "self.execution_dispatcher = ExecutionDispatcher" in text
assert "EXECUTION_MODE" in text

print("OK: pipeline has real execution components wired")
PY

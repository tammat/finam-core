#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text()

assert "self.execution_dispatcher.execute(intent=intent, market_state=st)" in text
assert "real_result = self.real_execution.execute(intent, st)" not in text

print("OK: pipeline uses ExecutionDispatcher for real execution route")
PY

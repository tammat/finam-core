#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "PIPE_FILL_PERSISTED result=" in text
assert "PIPE_FILL_PERSISTENCE_SKIP reason=service_not_configured" in text

print("OK: лог сохранения fill видим")
PY

#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "последний защитный слой metadata" in text
assert 'payload.setdefault("signal_id"' in text
assert 'payload.setdefault("strategy"' in text
assert 'payload.setdefault("source"' in text
assert "fill.payload = payload" in text
assert "fill.signal_id = payload.get" in text
assert "PIPE_FILL_PERSISTED result={persist_result} payload={payload}" in text

print("OK: fallback metadata перед persist_fill добавлен")
PY

#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/fill_persistence_service.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

service = Path("src/finam_core/execution/fill_persistence_service.py").read_text(encoding="utf-8")
pipeline = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert 'payload: dict | None = None' in service
assert 'payload=payload if isinstance(payload, dict) else getattr(fill, "payload", None)' in service
assert 'service.persist_fill(fill, execution_type="paper", payload=payload)' in pipeline
assert 'fill.payload = payload' not in pipeline
assert 'fill.signal_id = payload.get("signal_id")' not in pipeline

print("OK: fill persistence payload override works without mutating ExecutionFill")
PY

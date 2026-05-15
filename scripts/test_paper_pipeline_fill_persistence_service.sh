#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/execution/fill_persistence_service.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "from finam_core.execution.fill_persistence_service import FillPersistenceService" in text
assert "self.fill_persistence_service = FillPersistenceService(" in text
assert "service.persist_fill(fill, execution_type=\"paper\")" in text
assert "PIPE_FILL_PERSISTENCE_FAILED" in text
assert "PIPE_SIGNAL_FILL_LINK_FAILED" not in text

print("OK: paper_pipeline использует FillPersistenceService")
PY

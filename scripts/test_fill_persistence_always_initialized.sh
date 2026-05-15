#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "self.fill_persistence_service = FillPersistenceService(" in text
assert "PIPE_SIGNAL_REPOSITORY_INIT_FAILED" in text
assert "getattr(self.pg_logger, \"conn\", None)" in text

print("OK: FillPersistenceService создаётся независимо от SignalRepository")
PY

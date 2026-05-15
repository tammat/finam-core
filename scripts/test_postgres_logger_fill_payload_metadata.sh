#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/storage/postgres_logger.py \
  src/finam_core/execution/fill_persistence_service.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

logger = Path("src/finam_core/storage/postgres_logger.py").read_text(encoding="utf-8")
service = Path("src/finam_core/execution/fill_persistence_service.py").read_text(encoding="utf-8")
pipeline = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "extra_payload = kwargs.get(\"payload\")" in logger
assert "extra_payload = getattr(fill, \"payload\", None)" in logger
assert "**extra_payload" in logger

assert "payload=getattr(fill, \"payload\", None)" in service
assert "self.pg_logger.log_fill(" in service

assert "FillPersistenceService" in pipeline
assert "service.persist_fill(fill, execution_type=\"paper\")" in pipeline

print("OK: PostgresLogger и FillPersistenceService сохраняют metadata fill")
PY

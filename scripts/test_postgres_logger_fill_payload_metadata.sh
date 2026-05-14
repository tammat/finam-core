#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/storage/postgres_logger.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

logger = Path("src/finam_core/storage/postgres_logger.py").read_text(encoding="utf-8")
pipeline = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "extra_payload = kwargs.get(\"payload\")" in logger
assert "extra_payload = getattr(fill, \"payload\", None)" in logger
assert "**extra_payload" in logger
assert "payload=getattr(fill, \"payload\", None)" in pipeline

print("OK: postgres logger preserves fill payload metadata")
PY

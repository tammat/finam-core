#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert 'PIPE_SESSION_BLOCK:{session.get' in text
assert 'PIPE_SESSION_BLOCK_AFTER_ROUTER:{session.get' in text
assert 'SESSION_BLOCK_LOG_SEC' in text
assert 'print(f"PIPE_SESSION_BLOCK phase=' not in text
assert 'print(f"PIPE_SESSION_BLOCK_AFTER_ROUTER phase=' not in text

print("OK: PIPE_SESSION_BLOCK logs are deduplicated")
PY

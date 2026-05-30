#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_IMPULSE_FILTER_ADVISORY_PAPER_V1_START"

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text()

assert "IMPULSE_FILTER_ADVISORY_ONLY" in text
assert "PIPE_IMPULSE_ADVISORY_CONTINUE" in text
assert "impulse_advisory_only" in text
assert "paper_only=1" in text
assert 'str(os.getenv("EXECUTION_MODE", "paper")).lower() == "paper"' in text

print("TEST_IMPULSE_FILTER_ADVISORY_PAPER_V1_OK")
PY

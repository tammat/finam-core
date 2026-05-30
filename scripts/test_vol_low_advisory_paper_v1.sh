#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_VOL_LOW_ADVISORY_PAPER_V1_START"

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text()

assert "VOL_LOW_ADVISORY_ONLY" in text
assert "PIPE_VOL_LOW_ADVISORY_CONTINUE" in text
assert "vol_low_advisory_only" in text
assert "paper_only=1" in text

print("TEST_VOL_LOW_ADVISORY_PAPER_V1_OK")
PY

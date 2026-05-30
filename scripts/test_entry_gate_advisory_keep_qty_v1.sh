#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_ENTRY_GATE_ADVISORY_KEEP_QTY_V1_START"

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text()

assert "PIPE_ENTRY_GATE_ADVISORY_KEEP_ORIGINAL_QTY" in text
assert "entry_gate_advisory_only_qty" in text
assert "gate_qty" in text
assert "original_qty" in text

print("TEST_ENTRY_GATE_ADVISORY_KEEP_QTY_V1_OK")
PY

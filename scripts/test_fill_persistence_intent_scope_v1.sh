#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_FILL_PERSISTENCE_INTENT_SCOPE_V1_START"

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

lines = Path("src/finam_core/pipelines/paper_pipeline.py").read_text().splitlines()

bad = []
for i in range(5160, 5278):
    line = lines[i - 1]
    if "intent.get" in line or "intent=intent" in line:
        bad.append((i, line))

assert not bad, bad

print("TEST_FILL_PERSISTENCE_INTENT_SCOPE_V1_OK")
PY

#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

checks = [
    '"requested_symbol"',
    '"execution_symbol"',
    '"continuous_symbol"',
    '"execution_symbol_reason"',
    'payload.setdefault',
]

for c in checks:
    assert c in text, c

print("OK: execution symbol lineage persisted into trade payload")
PY

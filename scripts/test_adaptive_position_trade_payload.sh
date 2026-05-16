#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

checks = [
    'payload.setdefault("adaptive_position_base_qty"',
    'payload.setdefault("adaptive_position_final_qty"',
    'payload.setdefault("adaptive_position_multiplier"',
    'payload.setdefault("adaptive_position_reason"',
    'features.get("adaptive_position_multiplier")',
]

for c in checks:
    assert c in text, c

print("OK: adaptive_position fields persisted into trade payload")
PY

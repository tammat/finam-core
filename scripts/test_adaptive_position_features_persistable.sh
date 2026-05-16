#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/risk/adaptive_position_sizer.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

checks = [
    'features["adaptive_position_base_qty"]',
    'features["adaptive_position_final_qty"]',
    'features["adaptive_position_multiplier"]',
    'features["adaptive_position_reason"]',
    'intent["qty"] = decision.final_qty',
    'intent["quantity"] = decision.final_qty',
]

for c in checks:
    assert c in text, c

print("OK: adaptive_position fields are stored in intent.features")
PY

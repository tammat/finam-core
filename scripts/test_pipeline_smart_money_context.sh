#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path(
    "src/finam_core/pipelines/paper_pipeline.py"
).read_text(encoding="utf-8")

checks = [
    "_inject_latest_smart_money_context",
    "market_opportunity_metrics",
    "smart_money_score",
    "smart_money_label",
    "PIPE_SMART_MONEY_CONTEXT_ERROR",
]

for c in checks:
    assert c in text, c

inject_pos = text.find(
    "self._inject_latest_smart_money_context(intent)"
)

gate_pos = text.find(
    "_entry_confidence_gate_if_enabled(intent, st)"
)

assert inject_pos != -1
assert gate_pos != -1
assert inject_pos < gate_pos

print("OK: smart money context injected before confidence gate")
PY

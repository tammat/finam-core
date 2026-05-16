#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

checks = [
    "_inject_latest_institutional_flow_context",
    "institutional_flow_regime_events",
    "institutional_flow_regime",
    "institutional_flow_bias",
    "PIPE_INSTITUTIONAL_FLOW_CONTEXT_ERROR",
]

for c in checks:
    assert c in text, c

smart_pos = text.find("self._inject_latest_smart_money_context(intent)")
flow_pos = text.find("self._inject_latest_institutional_flow_context(intent)")
gate_pos = text.find("_entry_confidence_gate_if_enabled(intent, st)")

assert smart_pos < flow_pos < gate_pos

print("OK: institutional flow context injected before confidence gate")
PY

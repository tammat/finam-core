#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/strategy/signal_confidence.py \
  src/finam_core/strategy/entry_confidence_gate.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

checks = [
    "ENABLE_ENTRY_CONFIDENCE_GATE",
    "ENTRY_CONFIDENCE_MIN",
    "EntryConfidenceGate",
    "PIPE_ENTRY_CONFIDENCE_ACCEPT",
    "PIPE_ENTRY_CONFIDENCE_REJECT",
    "_entry_confidence_gate_if_enabled(intent, st)",
]

for c in checks:
    assert c in text, c

helper_pos = text.find("_entry_confidence_gate_if_enabled(intent, st)")
entry_gate_pos = text.find("ENTRY GATE COORDINATOR")

assert helper_pos != -1
assert entry_gate_pos != -1
assert helper_pos < entry_gate_pos

print("OK: paper_pipeline entry confidence gate before EntryGateCoordinator")
PY

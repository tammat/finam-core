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
    "ENABLE_ADAPTIVE_POSITION_SIZER",
    "AdaptivePositionSizer",
    "PIPE_ADAPTIVE_POSITION_SIZE",
    "adaptive_position_multiplier",
    "_adaptive_position_size_if_enabled(intent, st)",
]

for c in checks:
    assert c in text, c

confidence_pos = text.find("_entry_confidence_gate_if_enabled(intent, st)")
sizer_pos = text.find("_adaptive_position_size_if_enabled(intent, st)")
entry_gate_pos = text.find("ENTRY GATE COORDINATOR")

assert confidence_pos != -1
assert sizer_pos != -1
assert entry_gate_pos != -1
assert confidence_pos < sizer_pos < entry_gate_pos

print("OK: adaptive position sizer is after confidence gate and before EntryGateCoordinator")
PY

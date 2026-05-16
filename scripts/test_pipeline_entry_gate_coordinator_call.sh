#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/runtime/entry_gate_coordinator.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "ENTRY GATE COORDINATOR" in text
assert "gate.allow_entry(" in text
assert "PIPE_ENTRY_GATE_BLOCK" in text
assert "PIPE_ENTRY_GATE_COORDINATOR_ERROR" in text

first = text.find("raw_fill = self.paper.execute(intent, st)")
second = text.find("raw_fill = self.paper.execute(intent, st)", first + 1)
gate = text.find("ENTRY GATE COORDINATOR")

assert first != -1 and second != -1 and gate != -1
assert first < gate < second

print("OK: EntryGateCoordinator is inserted before entry-path raw_fill only")
PY

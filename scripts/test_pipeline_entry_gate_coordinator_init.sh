#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/runtime/entry_gate_coordinator.py \
  src/finam_core/runtime/regime_runtime_control_service.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "EntryGateCoordinator" in text
assert "RegimeRuntimeControlService" in text
assert "self.entry_gate_coordinator = EntryGateCoordinator(" in text
assert "regime_runtime_control_service=self.regime_runtime_control_service" in text

print("OK: paper_pipeline initializes EntryGateCoordinator")
PY

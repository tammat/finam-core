#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/runtime/entry_gate_coordinator.py \
  src/finam_core/runtime/trade_gate_service.py \
  src/finam_core/runtime/trend_gate_service.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

guard_pos = text.find("gate-сервисы должны существовать до создания EntryGateCoordinator")
init_pos = text.find("self.entry_gate_coordinator = EntryGateCoordinator(")

assert guard_pos != -1
assert init_pos != -1
assert guard_pos < init_pos
assert 'self.trade_gate_service = TradeGateService(' in text
assert 'self.trend_gate_service = TrendGateService()' in text

print("OK: EntryGateCoordinator init order is safe")
PY

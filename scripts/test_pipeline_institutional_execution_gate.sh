#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/risk/institutional_execution_gate.py \
  src/finam_core/risk/market_event_calendar_repository.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

checks = [
    "ENABLE_INSTITUTIONAL_EXECUTION_GATE",
    "MarketEventCalendarRepository",
    "InstitutionalExecutionGate",
    "PIPE_INSTITUTIONAL_EXECUTION_GATE",
    "institutional_execution_action",
    "institutional_execution_multiplier",
    "institutional_execution_reason",
    "market_event_type",
    "market_event_minutes_to_event",
    "_institutional_execution_gate_if_enabled(intent)",
]

for c in checks:
    assert c in text, c

flow_pos = text.find("self._inject_latest_institutional_flow_context(intent)")
resolver_pos = text.find("self._resolve_execution_symbol_if_enabled(intent, st)")
inst_pos = text.find("self._institutional_execution_gate_if_enabled(intent)")
adaptive_pos = text.find("self._adaptive_regime_filter_if_enabled(intent)")
confidence_pos = text.find("_entry_confidence_gate_if_enabled(intent, st)")

assert flow_pos < resolver_pos < inst_pos < adaptive_pos < confidence_pos

print("OK: institutional execution gate is before adaptive regime and confidence")
PY

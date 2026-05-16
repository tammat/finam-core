#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/execution/execution_symbol_resolver.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

checks = [
    "ENABLE_EXECUTION_SYMBOL_RESOLVER",
    "ExecutionSymbolResolver",
    "PIPE_EXECUTION_SYMBOL_RESOLVED",
    "requested_symbol",
    "execution_symbol",
    "_resolve_execution_symbol_if_enabled(intent, st)",
]

for c in checks:
    assert c in text, c

smart_pos = text.find("self._inject_latest_smart_money_context(intent)")
flow_pos = text.find("self._inject_latest_institutional_flow_context(intent)")
resolver_pos = text.find("self._resolve_execution_symbol_if_enabled(intent, st)")
confidence_pos = text.find("_entry_confidence_gate_if_enabled(intent, st)")
sizer_pos = text.find("_adaptive_position_size_if_enabled(intent, st)")
entry_gate_pos = text.find("ENTRY GATE COORDINATOR")

assert smart_pos < flow_pos < resolver_pos < confidence_pos < sizer_pos < entry_gate_pos

print("OK: execution symbol resolver before confidence/sizer/risk path")
PY

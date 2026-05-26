#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/validated_profile.py \
  src/finam_core/execution/edge_execution_gate.py

python - <<'PY'
from datetime import datetime, UTC
from finam_core.execution.edge_execution_gate import evaluate_edge_execution_gate

signal = {
    "symbol": "BRM6@RTSX",
    "strategy": "BR_CONSERVATIVE_BREAKOUT",
    "timeframe": "M5",
}

allowed = evaluate_edge_execution_gate(
    signal,
    datetime(2026, 5, 11, 9, 15, tzinfo=UTC),
)

assert allowed.allowed is True
assert allowed.reason == "validated_profile"

rejected = evaluate_edge_execution_gate(
    signal,
    datetime(2026, 5, 11, 15, 15, tzinfo=UTC),
)

assert rejected.allowed is False
assert rejected.reason == "unvalidated_profile"

missing = evaluate_edge_execution_gate(
    {"symbol": "BRM6@RTSX", "strategy": "BR_CONSERVATIVE_BREAKOUT"},
    datetime(2026, 5, 11, 9, 15, tzinfo=UTC),
)

assert missing.allowed is False
assert missing.reason == "missing_timeframe"

print("EDGE_EXECUTION_GATE_OK")
PY

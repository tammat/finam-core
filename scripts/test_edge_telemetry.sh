#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/edge_execution_gate.py \
  src/finam_core/execution/edge_telemetry.py

python - <<'PY'
from datetime import datetime, UTC

from finam_core.execution.edge_execution_gate import EdgeGateDecision
from finam_core.execution.edge_telemetry import (
    build_edge_telemetry_snapshot,
    merge_edge_telemetry,
)

decision = EdgeGateDecision(
    allowed=False,
    reason="unvalidated_profile",
    symbol="BRM6@RTSX",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    timeframe="M5",
    hour_utc=15,
)

ts = datetime(2026, 5, 26, 6, 30, tzinfo=UTC)

telemetry = build_edge_telemetry_snapshot(
    decision=decision,
    ts=ts,
    mode="soft",
)

payload = merge_edge_telemetry(
    payload={"trade_context_snapshot": {"existing": "ok"}},
    telemetry=telemetry,
)

edge = payload["trade_context_snapshot"]["edge_gate"]

assert payload["trade_context_snapshot"]["existing"] == "ok"
assert edge["mode"] == "soft"
assert edge["allowed"] is False
assert edge["reason"] == "unvalidated_profile"
assert edge["hour_utc"] == 15

print("EDGE_TELEMETRY_OK")
PY

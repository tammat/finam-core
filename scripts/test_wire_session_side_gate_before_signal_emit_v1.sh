#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_WIRE_SESSION_SIDE_GATE_BEFORE_SIGNAL_EMIT_V1_START"

python -m py_compile \
  src/finam_core/execution/session_side_execution_gate_v1.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

p = Path("src/finam_core/pipelines/paper_pipeline.py")
s = p.read_text(encoding="utf-8")

required = [
    "_check_session_side_execution_gate_v1",
    "PIPE_SESSION_SIDE_GATE_BLOCK",
]

missing = [x for x in required if x not in s]

if missing:
    raise SystemExit(f"MISSING_RUNTIME_GATE_WIRING: {missing}")

risk_reject_pos = s.find("PIPE_RISK_REJECT")
if risk_reject_pos == -1:
    raise SystemExit("PIPE_RISK_REJECT_NOT_FOUND")

risk_router_pos = s.rfind("decision = self.risk_router.route(", 0, risk_reject_pos)
if risk_router_pos == -1:
    raise SystemExit("RISK_ROUTER_BEFORE_PIPE_RISK_REJECT_NOT_FOUND")

gate_call_pos = s.rfind("if not self._check_session_side_execution_gate_v1(", 0, risk_router_pos)
if gate_call_pos == -1:
    raise SystemExit("GATE_CALL_BEFORE_TARGET_RISK_ROUTER_NOT_FOUND")

if not (gate_call_pos < risk_router_pos < risk_reject_pos):
    raise SystemExit("SESSION_SIDE_GATE_TARGET_ORDER_INVALID")

print("WIRE_SESSION_SIDE_GATE_BEFORE_SIGNAL_EMIT_RUNTIME_ORDER_OK")
PY

grep -n "_check_session_side_execution_gate_v1" \
  src/finam_core/pipelines/paper_pipeline.py | head -20

grep -n "PIPE_SESSION_SIDE_GATE_BLOCK" \
  src/finam_core/pipelines/paper_pipeline.py | head -20


echo "TEST_WIRE_SESSION_SIDE_GATE_BEFORE_SIGNAL_EMIT_V1_OK"

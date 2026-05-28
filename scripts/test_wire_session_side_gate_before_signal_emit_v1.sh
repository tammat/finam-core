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
    "signal_status = \"risk_rejected\"",
]

missing = [x for x in required if x not in s]

if missing:
    raise SystemExit(f"MISSING_RUNTIME_GATE_WIRING: {missing}")

risk_router_pos = s.find("self.risk_router.route(")
gate_pos = s.find("_check_session_side_execution_gate_v1")

if gate_pos == -1 or risk_router_pos == -1:
    raise SystemExit("UNABLE_TO_LOCATE_GATE_OR_RISK_ROUTER")

if gate_pos > risk_router_pos:
    raise SystemExit(
        "SESSION_SIDE_GATE_IS_AFTER_RISK_ROUTER"
    )

print("WIRE_SESSION_SIDE_GATE_BEFORE_SIGNAL_EMIT_RUNTIME_ORDER_OK")
PY

grep -n "_check_session_side_execution_gate_v1" \
  src/finam_core/pipelines/paper_pipeline.py | head -20

grep -n "PIPE_SESSION_SIDE_GATE_BLOCK" \
  src/finam_core/pipelines/paper_pipeline.py | head -20

grep -n "signal_status = \"risk_rejected\"" \
  src/finam_core/pipelines/paper_pipeline.py | head -20

echo "TEST_WIRE_SESSION_SIDE_GATE_BEFORE_SIGNAL_EMIT_V1_OK"

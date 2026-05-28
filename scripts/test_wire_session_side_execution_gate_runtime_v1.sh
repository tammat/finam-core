#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_WIRE_SESSION_SIDE_EXECUTION_GATE_RUNTIME_V1_START"

python -m py_compile \
  src/finam_core/execution/session_side_execution_gate_v1.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from finam_core.execution.session_side_execution_gate_v1 import SessionSideExecutionGateV1

data = json.loads(Path("runtime/session_side_execution_gate_v1.json").read_text(encoding="utf-8"))

allow = data["allow"][0]
block = data["block"][0]

gate = SessionSideExecutionGateV1("runtime/session_side_execution_gate_v1.json")

allow_decision = gate.decide(
    symbol=allow["symbol"],
    side=allow["entry_side"],
    ts=datetime(2026, 5, 28, int(allow["hour_msk"]), 0, tzinfo=ZoneInfo("Europe/Moscow")),
)

block_decision = gate.decide(
    symbol=block["symbol"],
    side=block["entry_side"],
    ts=datetime(2026, 5, 28, int(block["hour_msk"]), 0, tzinfo=ZoneInfo("Europe/Moscow")),
)

assert allow_decision.allowed is True, allow_decision
assert allow_decision.action == "ALLOW", allow_decision
assert block_decision.allowed is False, block_decision
assert block_decision.action == "BLOCK", block_decision

print("SESSION_SIDE_EXECUTION_GATE_RUNTIME_PY_OK")
PY

grep -q "SessionSideExecutionGateV1" src/finam_core/pipelines/paper_pipeline.py
grep -q "_extract_session_side_gate_side_v1" src/finam_core/pipelines/paper_pipeline.py
grep -q "_check_session_side_execution_gate_v1" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_SESSION_SIDE_GATE_DECISION" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_SESSION_SIDE_GATE_BLOCK" src/finam_core/pipelines/paper_pipeline.py
grep -q "self.risk_router.route" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_WIRE_SESSION_SIDE_EXECUTION_GATE_RUNTIME_V1_OK"

#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_WIRE_PHASE2_SOFT_BLOCK_TO_PIPELINE_V1_START"

python -m py_compile \
  src/finam_core/execution/runtime_edge_governance_soft_block_v1.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

p = Path("src/finam_core/pipelines/paper_pipeline.py")
s = p.read_text()

required = [
    "RuntimeEdgeGovernanceSoftBlockV1",
    "self.runtime_edge_governance_soft_block_v1 = RuntimeEdgeGovernanceSoftBlockV1()",
    "PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_DECISION",
    "PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_SOFT_BLOCK",
    "PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_FAILED_OPEN",
]

missing = [x for x in required if x not in s]
if missing:
    raise SystemExit(f"MISSING_PHASE2_WIRING: {missing}")

risk_reject_pos = s.find("PIPE_RISK_REJECT")
if risk_reject_pos == -1:
    raise SystemExit("PIPE_RISK_REJECT_NOT_FOUND")

risk_router_pos = s.rfind("decision = self.risk_router.route(", 0, risk_reject_pos)
if risk_router_pos == -1:
    raise SystemExit("TARGET_RISK_ROUTER_ROUTE_NOT_FOUND")

phase2_pos = s.rfind("PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_DECISION", 0, risk_router_pos)
session_gate_pos = s.rfind("if not self._check_session_side_execution_gate_v1(", 0, risk_router_pos)

if phase2_pos == -1:
    raise SystemExit("PHASE2_DECISION_BEFORE_RISK_ROUTER_NOT_FOUND")

if session_gate_pos == -1:
    raise SystemExit("SESSION_GATE_BEFORE_RISK_ROUTER_NOT_FOUND")

if not (phase2_pos < session_gate_pos < risk_router_pos < risk_reject_pos):
    raise SystemExit("PHASE2_ORDER_INVALID")

print("WIRE_PHASE2_SOFT_BLOCK_PIPELINE_ORDER_OK")
PY

grep -n "PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_DECISION" src/finam_core/pipelines/paper_pipeline.py | head -5
grep -n "PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_SOFT_BLOCK" src/finam_core/pipelines/paper_pipeline.py | head -5
grep -n "PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_FAILED_OPEN" src/finam_core/pipelines/paper_pipeline.py | head -5

echo "TEST_WIRE_PHASE2_SOFT_BLOCK_TO_PIPELINE_V1_OK"

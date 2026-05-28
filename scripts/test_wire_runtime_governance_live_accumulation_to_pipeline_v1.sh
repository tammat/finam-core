#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_WIRE_RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_TO_PIPELINE_V1_START"

python -m py_compile \
  src/finam_core/execution/runtime_governance_live_accumulation_v1.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

s = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

required = [
    "RuntimeGovernanceLiveAccumulatorV1",
    "RuntimeGovernanceLiveDecisionV1",
    "self.runtime_governance_live_accumulator_v1",
    "def _record_runtime_governance_live_accumulation_v1(",
    "PIPE_RUNTIME_EDGE_GOVERNANCE_LIVE_ACCUMULATION_FAILED_OPEN",
    "paper_pipeline_phase2_runtime",
    "runtime_governance_live_accumulation_v1_call",
]

missing = [x for x in required if x not in s]
if missing:
    raise SystemExit(f"MISSING_RUNTIME_GOVERNANCE_LIVE_WIRING: {missing}")

phase2_pos = s.find("PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_DECISION")
call_pos = s.find("runtime_governance_live_accumulation_v1_call")
soft_block_pos = s.find("PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_SOFT_BLOCK")

if not (phase2_pos != -1 and call_pos != -1 and soft_block_pos != -1):
    raise SystemExit("ORDER_MARKERS_NOT_FOUND")

if not (phase2_pos < call_pos < soft_block_pos):
    raise SystemExit("LIVE_ACCUMULATION_CALL_ORDER_INVALID")

print("WIRE_RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_STRUCTURE_OK")
PY

grep -n "runtime_governance_live_accumulation_v1" \
  src/finam_core/pipelines/paper_pipeline.py | head -20

echo "TEST_WIRE_RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_TO_PIPELINE_V1_OK"

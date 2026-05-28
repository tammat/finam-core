#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_EDGE_GATE_STRICT_MODE_CANDIDATE_V1_START"

python -m py_compile \
  src/finam_core/execution/edge_gate_strict_mode_v1.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from finam_core.execution.edge_gate_strict_mode_v1 import EdgeGateStrictModeV1

gate = EdgeGateStrictModeV1("runtime/edge_gate_strict_mode_v1.json")

allow = gate.evaluate(
    symbol="BR_ROLLING@RTSX",
    side="BUY",
    hour_msk=8,
)

block = gate.evaluate(
    symbol="BR_ROLLING@RTSX",
    side="BUY",
    hour_msk=19,
)

print(
    "STRICT_MODE_ALLOW",
    allow.allowed,
    allow.reason,
    allow.expectancy_points,
    allow.closed_trades,
)

print(
    "STRICT_MODE_BLOCK",
    block.allowed,
    block.reason,
    block.expectancy_points,
    block.closed_trades,
)

assert allow.allowed is True, allow
assert block.allowed is False, block

print("EDGE_GATE_STRICT_MODE_PY_OK")
PY

grep -q "EdgeGateStrictModeV1" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_EDGE_GATE_STRICT_MODE" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_EDGE_GATE_STRICT_MODE_FAILED_OPEN" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_EDGE_GATE_STRICT_MODE_CANDIDATE_V1_OK"

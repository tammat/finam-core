#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_EDGE_GOVERNANCE_PHASE2_SOFT_BLOCK_V1_START"

python -m py_compile \
  src/finam_core/execution/runtime_edge_governance_soft_block_v1.py \
  src/scripts/analytics/build_runtime_edge_governance_phase2_soft_block_v1.py

python - <<'PY'
from datetime import datetime
from zoneinfo import ZoneInfo

from finam_core.execution.runtime_edge_governance_soft_block_v1 import RuntimeEdgeGovernanceSoftBlockV1

gov = RuntimeEdgeGovernanceSoftBlockV1()

allow = gov.decide(
    symbol="BR_ROLLING@RTSX",
    side="BUY",
    ts=datetime(2026, 5, 28, 10, 0, tzinfo=ZoneInfo("Europe/Moscow")),
)

block = gov.decide(
    symbol="BR_ROLLING@RTSX",
    side="BUY",
    ts=datetime(2026, 5, 28, 19, 0, tzinfo=ZoneInfo("Europe/Moscow")),
)

print("PHASE2_ALLOW", allow.allowed, allow.reason, allow.action)
print("PHASE2_BLOCK", block.allowed, block.reason, block.action)

assert allow.allowed is True, allow
assert allow.action == "ALLOW", allow
assert block.allowed is False, block
assert block.action == "SOFT_BLOCK", block

print("RUNTIME_EDGE_GOVERNANCE_PHASE2_RUNTIME_OK")
PY

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_runtime_edge_governance_phase2_soft_block_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "RUNTIME_EDGE_GOVERNANCE_PHASE2_SOFT_BLOCK_V1" "$TMP_LOG"
grep -q "RUNTIME_EDGE_GOVERNANCE_PHASE2_ROW" "$TMP_LOG"
grep -q "RUNTIME_EDGE_GOVERNANCE_PHASE2_STATUS" "$TMP_LOG"
grep -q "RUNTIME_EDGE_GOVERNANCE_PHASE2_SOFT_BLOCK_V1_OK" "$TMP_LOG"

echo "TEST_RUNTIME_EDGE_GOVERNANCE_PHASE2_SOFT_BLOCK_V1_OK"

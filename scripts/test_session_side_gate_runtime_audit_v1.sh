#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_SESSION_SIDE_GATE_RUNTIME_AUDIT_V1_START"

python -m py_compile \
  src/finam_core/execution/session_side_execution_gate_v1.py \
  src/finam_core/execution/session_side_gate_runtime_audit_v1.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from datetime import datetime
from zoneinfo import ZoneInfo

from finam_core.execution.session_side_execution_gate_v1 import SessionSideExecutionGateV1
from finam_core.execution.session_side_gate_runtime_audit_v1 import SessionSideGateRuntimeAuditV1

gate = SessionSideExecutionGateV1("runtime/session_side_execution_gate_v1.json")
audit = SessionSideGateRuntimeAuditV1()

decision = gate.decide(
    symbol="BRN6@RTSX",
    side="BUY",
    ts=datetime(2026, 5, 28, 8, 0, tzinfo=ZoneInfo("Europe/Moscow")),
)

audit.save(
    decision=decision,
    source="test_session_side_gate_runtime_audit_v1",
    raw={"test": True},
)

print("SESSION_SIDE_GATE_RUNTIME_AUDIT_PY_OK")
PY

psql "$DATABASE_URL" -c "
select
  id,
  created_at,
  symbol,
  side,
  hour_msk,
  session_name,
  action,
  allowed,
  reason,
  source
from session_side_gate_runtime_audit_v1
order by id desc
limit 5;
"

grep -q "SessionSideGateRuntimeAuditV1" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_SESSION_SIDE_GATE_AUDIT_OK" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_SESSION_SIDE_GATE_AUDIT_FAILED" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_SESSION_SIDE_GATE_RUNTIME_AUDIT_V1_OK"

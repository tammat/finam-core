#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_GATE_SMOKE_TEST_V1_START"

python -m py_compile \
  src/finam_core/execution/session_side_execution_gate_v1.py \
  src/finam_core/execution/session_side_gate_runtime_audit_v1.py \
  src/finam_core/pipelines/paper_pipeline.py \
  src/scripts/analytics/build_session_side_gate_final_healthcheck_v1.py \
  src/scripts/analytics/build_session_side_gate_runtime_audit_summary_v1.py

python - <<'PY'
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from finam_core.execution.session_side_execution_gate_v1 import SessionSideExecutionGateV1
from finam_core.execution.session_side_gate_runtime_audit_v1 import SessionSideGateRuntimeAuditV1

print("RUNTIME_GATE_SMOKE_TEST_V1")

config_path = Path("runtime/session_side_execution_gate_v1.json")
data = json.loads(config_path.read_text(encoding="utf-8"))

assert data.get("allow"), "NO_ALLOW_ROWS_IN_GATE_CONFIG"
assert data.get("block"), "NO_BLOCK_ROWS_IN_GATE_CONFIG"

allow = data["allow"][0]
block = data["block"][0]

gate = SessionSideExecutionGateV1(config_path)

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

audit = SessionSideGateRuntimeAuditV1()

audit.save(
    decision=allow_decision,
    source="runtime_gate_smoke_test_v1",
    raw={"test": True, "case": "allow"},
)

audit.save(
    decision=block_decision,
    source="runtime_gate_smoke_test_v1",
    raw={"test": True, "case": "block"},
)

print(
    "RUNTIME_GATE_SMOKE_TEST_DECISIONS",
    f"allow_symbol={allow_decision.symbol}",
    f"allow_side={allow_decision.side}",
    f"allow_hour={allow_decision.hour_msk}",
    f"allow_action={allow_decision.action}",
    f"block_symbol={block_decision.symbol}",
    f"block_side={block_decision.side}",
    f"block_hour={block_decision.hour_msk}",
    f"block_action={block_decision.action}",
)

print("RUNTIME_GATE_SMOKE_TEST_V1_OK")
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
where source = 'runtime_gate_smoke_test_v1'
order by id desc
limit 10;
"

python src/scripts/analytics/build_session_side_gate_runtime_audit_summary_v1.py
python src/scripts/analytics/build_session_side_gate_final_healthcheck_v1.py

python src/scripts/analytics/cleanup_session_side_gate_runtime_audit_test_rows_v1.py

python src/scripts/analytics/build_session_side_gate_runtime_audit_summary_v1.py
python src/scripts/analytics/build_session_side_gate_final_healthcheck_v1.py

echo "TEST_RUNTIME_GATE_SMOKE_TEST_V1_OK"

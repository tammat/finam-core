#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=src

venv/bin/python - <<'PY'
from pathlib import Path

for name in (
    "src/marketcore/action/contract_v2.py",
    "src/marketcore/action/authorization_v2.py",
    "src/marketcore/action/policy_v2.py",
    "src/marketcore/action/dispatcher_v2.py",
    "src/marketcore/action/rollback_v2.py",
    "src/marketcore/action/postgres_risk_boundary_v2.py",
    "src/marketcore/action/handler_registry_v2.py",
    "src/marketcore/action/command_worker_v2.py",
    "src/marketcore/presentation/action_http_controller_v2.py",
):
    compile(Path(name).read_text(), name, "exec")
PY

venv/bin/pytest -q \
  tests/test_action_contract_v2.py \
  tests/test_action_policy_authorization_v2.py \
  tests/test_governed_action_dispatcher_v2.py \
  tests/test_governed_rollback_coordinator_v2.py \
  tests/test_postgres_action_governance_v2.py \
  tests/test_postgres_risk_boundary_v2.py \
  tests/test_state_changing_handler_registry_v2.py \
  tests/test_action_http_controller_v2.py \
  tests/test_governed_command_worker_v2.py

venv/bin/python - <<'PY'
from marketcore.action.handler_registry_v2 import state_changing_action_definitions_v2

definitions = state_changing_action_definitions_v2()
assert {item.command_code for item in definitions} == {
    "RESEARCH.REQUEST_REFRESH",
    "PAPER.REQUEST_OBSERVATION",
}
for item in definitions:
    forbidden = ("LIVE.", "BROKER.", "EXECUTION.")
    assert not item.command_code.startswith(forbidden), item.command_code
    assert item.rollback_code
PY

pending_requests="$(psql -d finam_core -Atqc "SELECT count(*) FROM marketcore_action.command_request_v2 WHERE status='PENDING'")"
test "$pending_requests" -eq 0
echo "pending_requests=$pending_requests"
systemctl is-active --quiet marketcore-governed-research-worker.timer
systemctl is-active --quiet marketcore-governed-paper-worker.timer

echo "action_contract=PASS"
echo "policy_authorization_risk=PASS"
echo "duplicate_guard_audit=PASS"
echo "rollback_pending_only=PASS"
echo "research_paper_workers=ACTIVE"
echo "live_broker_handlers=0"
echo "VERDICT=MARKETCORE_STAGE5_POLICY_GOVERNED_ACTIONS_COMPLETE"

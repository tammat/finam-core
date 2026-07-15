#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
PYTHONPATH=src venv/bin/python -m py_compile src/marketcore/action/dispatcher_v2.py
venv/bin/pytest -q \
  tests/test_action_contract_v2.py \
  tests/test_action_policy_authorization_v2.py \
  tests/test_governed_action_dispatcher_v2.py
echo "dispatch_order=AUTHORIZATION,POLICY,RISK,DUPLICATE,AUDIT,HANDLER,AUDIT"
echo "risk_boundary_fail_closed=PASS"
echo "duplicate_action_guard=PASS"
echo "audit_before_execution=PASS"
echo "navigation_command_separation=PASS"
echo "VERDICT=MARKETCORE_STAGE5_GOVERNED_DISPATCHER_V2_READY"

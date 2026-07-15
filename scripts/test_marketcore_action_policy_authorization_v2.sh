#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
PYTHONPATH=src venv/bin/python -m py_compile \
  src/marketcore/action/authorization_v2.py \
  src/marketcore/action/policy_v2.py
venv/bin/pytest -q tests/test_action_contract_v2.py tests/test_action_policy_authorization_v2.py
echo "authorization_boundary=PASS"
echo "least_privilege_scope=PASS"
echo "policy_fail_closed=PASS"
echo "approval_boundary=PASS"
echo "risk_guard_requirement=PASS"
echo "VERDICT=MARKETCORE_STAGE5_POLICY_AUTHORIZATION_V2_READY"

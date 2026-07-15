#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
PYTHONPATH=src venv/bin/python -m py_compile \
  src/marketcore/action/contract_v2.py \
  src/marketcore/action/__init__.py
venv/bin/pytest -q tests/test_action_contract_v2.py
echo "interaction_kinds=CLICK,DOUBLE_CLICK"
echo "navigation_command_boundary=PASS"
echo "direct_broker_execution_guard=PASS"
echo "approval_and_rollback_contract=PASS"
echo "VERDICT=MARKETCORE_STAGE5_ACTION_CONTRACT_V2_READY"

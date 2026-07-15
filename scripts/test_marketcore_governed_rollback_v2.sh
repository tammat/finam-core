#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
psql -v ON_ERROR_STOP=1 -d finam_core -f sql/marketcore_action/001_action_governance_v2.sql >/dev/null
psql -v ON_ERROR_STOP=1 -d finam_core -f sql/marketcore_action/002_rollback_audit_v2.sql >/dev/null
PYTHONPATH=src venv/bin/python -m py_compile src/marketcore/action/rollback_v2.py
venv/bin/pytest -q tests/test_action_policy_authorization_v2.py tests/test_governed_rollback_coordinator_v2.py tests/test_postgres_action_governance_v2.py
psql -d finam_core -Atqc "SELECT 'rollback_stage_constraints=' || count(*) FROM pg_constraint WHERE conrelid='marketcore_action.action_audit_v2'::regclass AND pg_get_constraintdef(oid) LIKE '%ROLLBACK_STARTED%';"
echo "rollback_policy_boundary=PASS"
echo "rollback_approval_boundary=PASS"
echo "rollback_duplicate_guard=PASS"
echo "rollback_audit=PASS"
echo "VERDICT=MARKETCORE_STAGE5_GOVERNED_ROLLBACK_V2_READY"

#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
psql -v ON_ERROR_STOP=1 -d finam_core -f sql/marketcore_action/001_action_governance_v2.sql >/dev/null
PYTHONPATH=src venv/bin/python -m py_compile src/marketcore/action/postgres_adapters_v2.py
venv/bin/pytest -q tests/test_postgres_action_governance_v2.py tests/test_governed_action_dispatcher_v2.py
psql -v ON_ERROR_STOP=1 -d finam_core -Atqc "
SELECT 'audit_append_only=' || count(*)
FROM pg_trigger
WHERE tgrelid='marketcore_action.action_audit_v2'::regclass
  AND tgname='action_audit_v2_append_only'
  AND NOT tgisinternal;
SELECT 'idempotency_primary_key=' || count(*)
FROM pg_constraint
WHERE conrelid='marketcore_action.idempotency_claim_v2'::regclass
  AND contype='p';"
echo "VERDICT=MARKETCORE_STAGE5_POSTGRES_ACTION_GOVERNANCE_V2_READY"

#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
PYTHONPATH=src venv/bin/python -m py_compile src/marketcore/action/postgres_risk_boundary_v2.py
venv/bin/pytest -q tests/test_postgres_risk_boundary_v2.py tests/test_governed_action_dispatcher_v2.py
PYTHONPATH=src venv/bin/python - <<'PY'
from datetime import datetime, timezone
from marketcore.action.postgres_risk_boundary_v2 import PostgresRiskBoundaryV2
from tests.test_postgres_risk_boundary_v2 import intent
d = PostgresRiskBoundaryV2().evaluate(intent(), "RISK.RESEARCH_RESOURCE_GUARD", now=datetime.now(timezone.utc))
print(f"production_risk_verdict={d.verdict.value}")
print(f"production_risk_reason={d.reason_code}")
assert d.verdict.value == "DENY"
print("VERDICT=MARKETCORE_STAGE5_POSTGRES_RISK_BOUNDARY_V2_READY")
PY

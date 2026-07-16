#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
psql -v ON_ERROR_STOP=1 -d finam_core -f sql/analytics/060_operator_decision_workspace_v2.sql >/dev/null
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src venv/bin/pytest -q tests/test_operator_decision_workspace_v2.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src venv/bin/python src/scripts/build_operator_decision_workspace_v2.py
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.operator_decision_workspace_v2")" -eq 5
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.operator_decision_workspace_v2 WHERE quality_code<>'UNVERIFIED' OR policy_verdict NOT IN ('REVIEW_REQUIRED','BLOCKED')")" -eq 0
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.operator_decision_workspace_v2 WHERE source_as_of IS NULL OR expires_at<=updated_at OR rollback_plan_code='' OR evidence='{}'::jsonb")" -eq 0
echo "ranked_actions=5"
echo "green_unverified_actions=0"
echo "autonomous_live_actions=0"
echo "VERDICT=MARKETCORE_STAGE8_OPERATOR_DECISION_WORKSPACE_V2_READY"

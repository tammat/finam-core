#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
psql -v ON_ERROR_STOP=1 -d finam_core -f sql/analytics/058_profit_funnel_paper_runtime_admission_v2.sql >/dev/null
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src venv/bin/pytest -q tests/test_paper_runtime_admission_v2.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src venv/bin/python src/scripts/build_profit_funnel_paper_runtime_admission_v2.py
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.paper_runtime_candidate_v1 p JOIN analytics.edge_candidate_v1 c USING(observation_uuid) WHERE p.paper_status='ACTIVE' AND (c.candidate_status='OOS_FAIL' OR NOT c.paper_allowed)")" -eq 0
eligible="$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.paper_runtime_candidate_v1 p JOIN analytics.edge_candidate_v1 c USING(observation_uuid) WHERE p.paper_status='ACTIVE' AND c.candidate_status='OOS_PASS' AND c.paper_allowed")"
pending="$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.profit_funnel_paper_runtime_admission_v2 WHERE admission_status='PENDING' AND NOT runtime_allowed AND NOT execution_enabled AND NOT live_allowed")"
test "$eligible" -eq "$pending"
echo "paper_candidates_eligible=$eligible"
echo "runtime_admission_pending=$pending"
echo "execution_changed=0"
echo "VERDICT=MARKETCORE_STAGE7_PAPER_RUNTIME_ADMISSION_V2_READY"

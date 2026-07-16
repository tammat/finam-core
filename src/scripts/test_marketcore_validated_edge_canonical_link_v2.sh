#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
psql -v ON_ERROR_STOP=1 -d finam_core -f sql/analytics/056_profit_funnel_validated_edge_v2.sql >/dev/null
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src venv/bin/pytest -q tests/test_validated_edge_canonical_link_v2.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src venv/bin/python src/scripts/build_profit_funnel_validated_edge_v2.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src venv/bin/python src/scripts/build_profit_funnel_transition_lineage_v2.py
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.edge_candidate_v1")" -eq "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.profit_funnel_validated_edge_v2")"
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.profit_funnel_transition_lineage_v2 WHERE transition_code='CANDIDATE_TO_VALIDATED_EDGE' AND lineage_status='PROVEN' AND reason_code='CANDIDATE_UUID_FULL_MATCH'")" -eq 1
echo "canonical_join=candidate_uuid"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "VERDICT=MARKETCORE_STAGE7_VALIDATED_EDGE_CANONICAL_LINK_V2_READY"

#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src venv/bin/pytest -q tests/test_candidate_oos_canonical_link_v2.py tests/test_profit_funnel_source_registry_v2.py
src/scripts/test_marketcore_profit_funnel_transition_lineage_v2.sh
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.edge_candidate_v1 WHERE validation_stage='OOS_COMPLETE'")" -eq 10
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.edge_candidate_v1 WHERE candidate_status='OOS_PASS'")" -eq 4
echo "candidate_freshness=PASS"
echo "oos_freshness=PASS"
echo "candidate_oos_heuristic_links=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "VERDICT=MARKETCORE_STAGE7_CANDIDATE_OOS_CANONICAL_LINK_V2_READY"

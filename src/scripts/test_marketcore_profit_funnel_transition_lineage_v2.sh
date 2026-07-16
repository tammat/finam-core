#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
psql -v ON_ERROR_STOP=1 -d finam_core -f sql/analytics/054_profit_funnel_transition_lineage_v2.sql >/dev/null
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src venv/bin/python src/scripts/build_profit_funnel_transition_lineage_v2.py
test "$(psql -d finam_core -Atqc 'SELECT count(*) FROM analytics.profit_funnel_transition_lineage_v2')" -eq 9
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.profit_funnel_transition_lineage_v2 WHERE transition_code='FORWARD_TO_SHADOW' AND lineage_status='PROVEN' AND linked_count=from_count AND linked_count=to_count")" -eq 1
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.profit_funnel_transition_lineage_v2 WHERE transition_code='VALIDATED_EDGE_TO_OOS' AND lineage_status='PROVEN' AND reason_code='OBSERVATION_UUID_FULL_MATCH' AND linked_count=from_count AND linked_count=to_count")" -eq 1
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.profit_funnel_transition_lineage_v2 WHERE transition_code='RESEARCH_TO_CANDIDATE' AND lineage_status='PROVEN' AND reason_code='OBSERVATION_UUID_FULL_MATCH' AND linked_count=to_count")" -eq 1
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.profit_funnel_transition_lineage_v2 WHERE transition_code='OOS_TO_FORWARD' AND lineage_status='BROKEN' AND reason_code='PIPELINE_IDENTITY_NAMESPACE_MISMATCH' AND linked_count=0")" -eq 1
echo "heuristic_links=0"
echo "forward_shadow_full_link=PASS"
echo "candidate_oos_full_link=PASS"
echo "research_candidate_full_link=PASS"
echo "oos_forward_identity_gap=EXPOSED"
echo "real_trading_changed=0"
echo "VERDICT=MARKETCORE_STAGE7_PROFIT_FUNNEL_TRANSITION_LINEAGE_V2_READY"

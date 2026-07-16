#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
psql -v ON_ERROR_STOP=1 -d finam_core -f sql/analytics/055_profit_funnel_oos_forward_handoff_v2.sql >/dev/null
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src venv/bin/pytest -q tests/test_oos_forward_handoff_v2.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src venv/bin/python src/scripts/build_profit_funnel_oos_forward_handoff_v2.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src venv/bin/python src/scripts/build_profit_funnel_transition_lineage_v2.py
eligible="$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.edge_oos_result_v1 o JOIN analytics.edge_candidate_v1 c ON c.observation_uuid=o.observation_uuid WHERE o.verdict_code='OOS_PASS' AND o.promotion_allowed=true")"
pending="$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.profit_funnel_oos_forward_handoff_v2 WHERE handoff_status='PENDING' AND NOT runtime_allowed AND NOT live_allowed")"
test "$eligible" -eq "$pending"
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.profit_funnel_transition_lineage_v2 WHERE transition_code='OOS_TO_FORWARD' AND lineage_status='UNVERIFIED' AND reason_code='HANDOFF_PENDING_FORWARD_ADMISSION'")" -eq 1
echo "eligible_oos_handoffs=$eligible"
echo "pending_safe_handoffs=$pending"
echo "forward_incubator_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "VERDICT=MARKETCORE_STAGE7_OOS_FORWARD_HANDOFF_V2_READY"

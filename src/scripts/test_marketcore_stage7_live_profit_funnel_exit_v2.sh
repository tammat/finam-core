#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src venv/bin/pytest -q \
  tests/test_profit_funnel_contract_v2.py \
  tests/test_profit_funnel_source_registry_v2.py \
  tests/test_control_center_profit_funnel_v2.py \
  tests/test_validated_edge_canonical_link_v2.py \
  tests/test_oos_forward_handoff_v2.py \
  tests/test_shadow_paper_admission_v2.py \
  tests/test_paper_runtime_admission_v2.py \
  tests/test_runtime_live_admission_v2.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src venv/bin/python src/scripts/build_profit_funnel_transition_lineage_v2.py

test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.profit_funnel_transition_lineage_v2")" -eq 9
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.profit_funnel_transition_lineage_v2 WHERE lineage_status='BROKEN'")" -eq 0
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.profit_funnel_transition_lineage_v2 WHERE lineage_status='PROVEN'")" -eq 4
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.profit_funnel_transition_lineage_v2 WHERE lineage_status='UNVERIFIED' AND reason_code IN ('HANDOFF_PENDING_FORWARD_ADMISSION','NO_SHADOW_CANDIDATE_ELIGIBLE','RUNTIME_ADMISSION_PENDING','NO_RUNTIME_CANDIDATE_ADMITTED','NO_REAL_EXECUTION')")" -eq 5
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM public.orders WHERE exchange_order_id IS NOT NULL")" -eq 0
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.profit_factory_profit_fact_v1 WHERE data_scope='REAL'")" -eq 0
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.profit_funnel_oos_forward_handoff_v2 WHERE runtime_allowed OR live_allowed")" -eq 0
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.profit_funnel_shadow_paper_admission_v2 WHERE paper_allowed OR runtime_allowed OR live_allowed")" -eq 0
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.profit_funnel_paper_runtime_admission_v2 WHERE runtime_allowed OR execution_enabled OR live_allowed")" -eq 0
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.profit_funnel_runtime_live_admission_v2 WHERE broker_order_allowed OR execution_enabled OR live_allowed")" -eq 0

echo "canonical_stages=10"
echo "canonical_transitions=9"
echo "lineage_proven=4"
echo "lineage_governed_blockers=5"
echo "lineage_broken=0"
echo "render_tree_profit_funnel=PASS"
echo "real_trading_changed=0"
echo "VERDICT=MARKETCORE_STAGE7_LIVE_PROFIT_FUNNEL_EXIT_GATE_PASS"

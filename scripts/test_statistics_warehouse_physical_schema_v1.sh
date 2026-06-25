#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_STATISTICS_WAREHOUSE_PHYSICAL_SCHEMA_V1 ==="

PYTHONPATH=src src/scripts/research/build_statistics_warehouse_physical_schema_v1.py --save \
  | tee /tmp/statistics_warehouse_physical_schema_v1.out

grep -q "STATISTICS_WAREHOUSE_PHYSICAL_SCHEMA_V1" /tmp/statistics_warehouse_physical_schema_v1.out
grep -q "mode=save" /tmp/statistics_warehouse_physical_schema_v1.out
grep -q "table_qlt_workflow_event_v1=true" /tmp/statistics_warehouse_physical_schema_v1.out
grep -q "table_nrm_workflow_event_v1=true" /tmp/statistics_warehouse_physical_schema_v1.out
grep -q "table_fact_event_workflow_stage_v1=true" /tmp/statistics_warehouse_physical_schema_v1.out
grep -q "table_fact_event_workflow_transition_v1=true" /tmp/statistics_warehouse_physical_schema_v1.out
grep -q "table_fact_state_candidate_lifecycle_v1=true" /tmp/statistics_warehouse_physical_schema_v1.out
grep -q "table_dim_stage_v1=true" /tmp/statistics_warehouse_physical_schema_v1.out
grep -q "table_sem_workflow_v1=true" /tmp/statistics_warehouse_physical_schema_v1.out
grep -q "table_mart_workflow_dashboard_v1=true" /tmp/statistics_warehouse_physical_schema_v1.out
grep -q "table_snap_workflow_daily_v1=true" /tmp/statistics_warehouse_physical_schema_v1.out
grep -q "workflow_domain_only=1" /tmp/statistics_warehouse_physical_schema_v1.out
grep -q "market_trade_edge_deferred=1" /tmp/statistics_warehouse_physical_schema_v1.out
grep -q "incremental_ready=1" /tmp/statistics_warehouse_physical_schema_v1.out
grep -q "runtime_changed=0" /tmp/statistics_warehouse_physical_schema_v1.out
grep -q "execution_changed=0" /tmp/statistics_warehouse_physical_schema_v1.out
grep -q "orders_changed=0" /tmp/statistics_warehouse_physical_schema_v1.out
grep -q "fills_changed=0" /tmp/statistics_warehouse_physical_schema_v1.out
grep -q "micro_live_allowed=0" /tmp/statistics_warehouse_physical_schema_v1.out
grep -q "VERDICT=STATISTICS_WAREHOUSE_PHYSICAL_SCHEMA_V1_READY" /tmp/statistics_warehouse_physical_schema_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'warehouse_table_count=' || count(*)
FROM information_schema.tables
WHERE table_schema='warehouse';

SELECT 'stage_fact_columns=' || string_agg(column_name, ',' ORDER BY ordinal_position)
FROM information_schema.columns
WHERE table_schema='warehouse'
  AND table_name='fact_event_workflow_stage_v1';

SELECT 'mart_columns=' || string_agg(column_name, ',' ORDER BY ordinal_position)
FROM information_schema.columns
WHERE table_schema='warehouse'
  AND table_name='mart_workflow_dashboard_v1';
SQL

echo "TEST_STATISTICS_WAREHOUSE_PHYSICAL_SCHEMA_V1_OK"

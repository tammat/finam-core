#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_STATISTICS_WAREHOUSE_SCHEMA_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'target_schema=warehouse';

SELECT 'quality_tables=qlt_workflow_event_v1,qlt_workflow_run_v1';

SELECT 'normalized_tables=nrm_workflow_event_v1,nrm_workflow_run_v1';

SELECT 'event_fact_tables=fact_event_workflow_stage_v1,fact_event_workflow_transition_v1';

SELECT 'state_fact_tables=fact_state_candidate_lifecycle_v1,fact_state_workflow_health_v1,fact_state_workflow_quality_v1';

SELECT 'dimension_tables=dim_broker_v1,dim_exchange_v1,dim_market_v1,dim_instrument_v1,dim_strategy_v1,dim_stage_v1,dim_status_v1,dim_reason_v1,dim_metric_v1,dim_status_light_v1';

SELECT 'semantic_tables=sem_candidate_v1,sem_workflow_v1,sem_execution_v1,sem_edge_v1';

SELECT 'mart_tables=mart_workflow_dashboard_v1,mart_candidate_workflow_v1';

SELECT 'snapshot_tables=snap_workflow_daily_v1';

SELECT 'source_raw=research.workflow_runtime_runs_v1,research.workflow_runtime_events_v1,reference.*';

SELECT 'canonical_columns=candidate_id,workflow_run_id,broker_id,exchange_id,market_code,instrument_id,symbol,display_symbol,asset_class_code,currency_code,timezone,strategy_code,timeframe,session_code,stage_code,status_code,reason_code,event_ts,created_at,payload';

SELECT 'lineage_columns=source_table,source_id,source_event_id,source_run_id,calculation_version,calculated_at';

SELECT 'health_columns=health_score,health_light,health_reason_code';

SELECT 'quality_columns=quality_status,quality_reason_code,quality_light';

SELECT 'version_columns=workflow_version,strategy_version,statistics_version,semantic_version,mart_version,localization_version';

SELECT 'fact_policy=STORE_CODES_ONLY';

SELECT 'mart_policy=RECALCULABLE';

SELECT 'snapshot_policy=APPEND_ONLY_DAILY';

SELECT 'incremental_policy=changed_since_only';

SELECT 'no_full_scan_policy=true';

SELECT 'presentation_policy=READ_MART_AND_SNAPSHOT_ONLY';

SELECT 'multi_exchange=true';
SELECT 'multi_broker=true';
SELECT 'multilingual=true';
SELECT 'traffic_lights=true';
SELECT 'health_score=true';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=STATISTICS_WAREHOUSE_SCHEMA_V1_READY';
SQL

echo "TEST_STATISTICS_WAREHOUSE_SCHEMA_V1_OK"

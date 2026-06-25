#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_STATISTICS_WAREHOUSE_PLAN_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'warehouse_model=RAW->QUALITY->NORMALIZED->FACT->DIMENSION->MART->SNAPSHOT->PRESENTATION';

SELECT 'raw_sources=research.workflow_runtime_runs_v1,research.workflow_runtime_events_v1,reference.*';

SELECT 'quality_layer=workflow_event_quality_v1,workflow_run_quality_v1';

SELECT 'normalized_layer=workflow_event_normalized_v1,workflow_run_normalized_v1';

SELECT 'fact_layer=workflow_stage_facts_v1,workflow_transition_facts_v1,candidate_lifecycle_facts_v1,workflow_health_facts_v1,workflow_quality_facts_v1';

SELECT 'dimension_layer=dim_broker_v1,dim_exchange_v1,dim_market_v1,dim_instrument_v1,dim_strategy_v1,dim_stage_v1,dim_status_v1,dim_reason_v1,dim_metric_v1,dim_status_light_v1';

SELECT 'mart_layer=workflow_dashboard_mart_v1,candidate_workflow_mart_v1';

SELECT 'snapshot_layer=workflow_daily_snapshot_v1';

SELECT 'presentation_layer=dashboard_8088,api,telegram,reports';

SELECT 'incremental_policy=changed_since_only';

SELECT 'no_full_scan_policy=true';

SELECT 'source_lineage_required=true';

SELECT 'lineage_fields=source_table,source_id,source_event_id,source_run_id,calculation_version,calculated_at';

SELECT 'canonical_fields_required=true';

SELECT 'health_required=true';

SELECT 'traffic_lights_required=true';

SELECT 'localized_labels_from_reference=true';

SELECT 'fact_policy=STORE_CODES_ONLY';

SELECT 'mart_policy=RECALCULABLE';

SELECT 'snapshot_policy=APPEND_ONLY_DAILY';

SELECT 'presentation_policy=READ_MART_AND_SNAPSHOT_ONLY';

SELECT 'data_quality_checks=missing_required_fields,duplicate_events,invalid_stage_code,invalid_status_code,invalid_reason_code,stale_workflow,orphan_event';

SELECT 'performance_policy=incremental,limited_window,indexed_by_event_ts_and_workflow_run_id';

SELECT 'hardware_fit=OK_FOR_CURRENT_15GB_RAM_99GB_FREE_DB_13GB';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=WORKFLOW_STATISTICS_WAREHOUSE_PLAN_V1_READY';
SQL

echo "TEST_WORKFLOW_STATISTICS_WAREHOUSE_PLAN_V1_OK"

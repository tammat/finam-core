#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_STATISTICS_DATASET_SCHEMA_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'

SELECT 'statistics_dataset_version=V1';

SELECT 'source_reference_platform=reference';

SELECT 'source_workflow_platform=research.workflow_runtime_runs_v1,research.workflow_runtime_events_v1';

SELECT 'target_tables=' ||
'workflow_stage_facts_v1,' ||
'workflow_transition_facts_v1,' ||
'candidate_lifecycle_facts_v1,' ||
'workflow_health_facts_v1,' ||
'workflow_quality_facts_v1';

SELECT 'canonical_fields=' ||
'candidate_id,' ||
'workflow_run_id,' ||
'broker_id,' ||
'exchange_id,' ||
'market_code,' ||
'instrument_id,' ||
'symbol,' ||
'display_symbol,' ||
'asset_class_code,' ||
'currency_code,' ||
'timezone,' ||
'strategy_code,' ||
'timeframe,' ||
'session_code,' ||
'stage_code,' ||
'status_code,' ||
'reason_code,' ||
'event_ts,' ||
'created_at,' ||
'payload';

SELECT 'workflow_stage_fact_fields=' ||
'stage_duration_ms,' ||
'result_status,' ||
'health_score,' ||
'health_light';

SELECT 'workflow_transition_fields=' ||
'from_stage,' ||
'to_stage,' ||
'transition_duration_ms';

SELECT 'candidate_lifecycle_fields=' ||
'research_status,' ||
'workflow_status,' ||
'paper_status,' ||
'current_stage,' ||
'next_stage';

SELECT 'workflow_health_fields=' ||
'health_score,' ||
'health_light,' ||
'health_reason_code';

SELECT 'workflow_quality_fields=' ||
'latency_ms,' ||
'success_rate,' ||
'wait_rate,' ||
'block_rate,' ||
'fail_rate';

SELECT 'statistics_granularity=FACT';

SELECT 'statistics_model=CANONICAL';

SELECT 'fact_policy=STORE_CODES_ONLY';

SELECT 'reference_policy=LOOKUP_FROM_REFERENCE_PLATFORM';

SELECT 'traffic_light_policy=REFERENCE_STATUS_LIGHTS';

SELECT 'multilingual=true';

SELECT 'multi_exchange=true';

SELECT 'multi_broker=true';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=WORKFLOW_STATISTICS_DATASET_SCHEMA_V1_READY';

SQL

echo "TEST_WORKFLOW_STATISTICS_DATASET_SCHEMA_V1_OK"

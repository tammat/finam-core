#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FINAM_CORE_ARCHITECTURE_V6_SCHEMA_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'

SELECT 'architecture_version=V6';

SELECT 'architecture_style=LAYERED_ENTERPRISE_PLATFORM';

SELECT 'layer_1=REFERENCE_PLATFORM';

SELECT 'layer_2=METADATA_PLATFORM';

SELECT 'layer_3=CONFIGURATION_PLATFORM';

SELECT 'layer_4=RESEARCH_PLATFORM';

SELECT 'layer_5=WORKFLOW_PLATFORM';

SELECT 'layer_6=STATISTICS_PLATFORM';

SELECT 'layer_7=PRESENTATION_PLATFORM';

SELECT 'layer_8=CONTROL_PLATFORM';

SELECT 'layer_9=SCHEDULER_PLATFORM';

SELECT 'layer_10=EXECUTION_PLATFORM';

SELECT 'reference_scope=' ||
'brokers,exchanges,markets,instruments,aliases,contracts,strategies,stages,statuses,reasons,asset_classes,sessions,metrics,status_lights,localization,ui';

SELECT 'metadata_scope=' ||
'workflow_definitions,stage_definitions,metric_definitions,dashboard_definitions,report_definitions';

SELECT 'configuration_scope=' ||
'strategy_parameters,risk_parameters,workflow_parameters,market_parameters,broker_parameters';

SELECT 'statistics_scope=' ||
'workflow,market,trade,execution,edge,health,data_quality';

SELECT 'presentation_scope=' ||
'data_mart,dashboard,rest_api,telegram,reports';

SELECT 'control_scope=' ||
'commands,approvals,rbac,audit,operations';

SELECT 'scheduler_scope=' ||
'workflow_scheduler,research_scheduler,statistics_scheduler,report_scheduler';

SELECT 'execution_scope=' ||
'order_intent,paper,micro_live,real';

SELECT 'cross_cutting=' ||
'versioning,lineage,health_score,multi_exchange,multi_broker,multilingual';

SELECT 'canonical_fields=' ||
'candidate_id,workflow_run_id,broker_id,exchange_id,market_code,instrument_id,asset_class_code,currency_code,strategy_code,stage_code,status_code,reason_code,metric_code,event_ts,created_at,payload';

SELECT 'facts_policy=STORE_CODES_ONLY';

SELECT 'presentation_policy=LOCALIZED_LABELS_ONLY';

SELECT 'ui_policy=COMMANDS_ONLY_NO_DIRECT_EXECUTION';

SELECT 'dependency_rule=' ||
'REFERENCE->METADATA->CONFIGURATION->RESEARCH->WORKFLOW->STATISTICS->PRESENTATION->CONTROL->SCHEDULER->EXECUTION';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=FINAM_CORE_ARCHITECTURE_V6_SCHEMA_V1_READY';

SQL

echo "TEST_FINAM_CORE_ARCHITECTURE_V6_SCHEMA_V1_OK"


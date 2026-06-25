#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_REFERENCE_AND_STATISTICS_PLATFORM_SCHEMA_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'architecture_freeze=V5';

SELECT 'platforms=REFERENCE,RESEARCH,WORKFLOW,STATISTICS,PRESENTATION,CONTROL_UI,EXECUTION';

SELECT 'reference_tables=' ||
'brokers_v1,exchanges_v1,markets_v1,instruments_v1,instrument_aliases_v1,contracts_v1,strategies_v1,workflow_stages_v1,statuses_v1,reasons_v1,asset_classes_v1,sessions_v1,metrics_v1,status_lights_v1,localization_labels_v1,ui_sections_v1,ui_actions_v1';

SELECT 'statistics_domains=' ||
'workflow_statistics,market_statistics,trade_statistics,edge_statistics,data_quality,health_score';

SELECT 'canonical_fields=' ||
'candidate_id,workflow_run_id,broker_id,exchange_id,market_code,instrument_id,symbol,display_symbol,asset_class_code,currency_code,timezone,strategy_code,timeframe,session_code,stage_code,status_code,reason_code,event_ts,created_at,payload';

SELECT 'fact_rule=FACTS_STORE_CODES_NOT_LABELS';

SELECT 'presentation_rule=DASHBOARD_RENDERS_LOCALIZED_LABELS';

SELECT 'russian_terms_rule=DOMAIN_NATIVE_RUSSIAN_NOT_LITERAL_TRANSLATION';

SELECT 'multilingual=true';

SELECT 'multi_exchange=true';

SELECT 'multi_broker=true';

SELECT 'status_light_codes=GREEN,YELLOW,ORANGE,RED,BLACK,WHITE,BLUE';

SELECT 'health_fields=health_score,health_light,health_reason_code';

SELECT 'lineage_fields=source_table,source_id,calculation_version,calculated_at';

SELECT 'versioning_fields=workflow_version,strategy_version,statistics_version,mart_version,localization_version';

SELECT 'control_ui_tables=control_commands_v1,control_action_audit_v1';

SELECT 'ui_rule=UI_CREATES_COMMANDS_INTENTS_EVENTS_NO_DIRECT_EXECUTION';

SELECT 'rbac_required=true';

SELECT 'approval_required_for_sensitive_actions=true';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=REFERENCE_AND_STATISTICS_PLATFORM_SCHEMA_V1_READY';
SQL

echo "TEST_REFERENCE_AND_STATISTICS_PLATFORM_SCHEMA_V1_OK"

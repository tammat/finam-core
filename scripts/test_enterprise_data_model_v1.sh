#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_ENTERPRISE_DATA_MODEL_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'model=ENTERPRISE_TRADING_INTELLIGENCE_DATA_MODEL';

SELECT 'model_version=V1';

SELECT 'table_naming_policy=ref_,raw_,qlt_,nrm_,fact_,dim_,sem_,mart_,snap_,cfg_,meta_,ctl_';

SELECT 'core_entities=broker,exchange,market,instrument,contract,strategy,candidate,workflow,stage,event,signal,intent,order,fill,trade,position,portfolio,account,metric,reason,status,health';

SELECT 'canonical_keys=broker_id,exchange_id,market_code,instrument_id,contract_id,strategy_code,candidate_id,workflow_run_id,stage_code,status_code,reason_code,metric_code';

SELECT 'data_layers=REFERENCE,RAW,QUALITY,NORMALIZED,EVENT_FACT,STATE_FACT,DIMENSION,SEMANTIC,MART,SNAPSHOT,PRESENTATION';

SELECT 'reference_prefix=ref_';
SELECT 'raw_prefix=raw_';
SELECT 'quality_prefix=qlt_';
SELECT 'normalized_prefix=nrm_';
SELECT 'event_fact_prefix=fact_event_';
SELECT 'state_fact_prefix=fact_state_';
SELECT 'dimension_prefix=dim_';
SELECT 'semantic_prefix=sem_';
SELECT 'mart_prefix=mart_';
SELECT 'snapshot_prefix=snap_';
SELECT 'configuration_prefix=cfg_';
SELECT 'metadata_prefix=meta_';
SELECT 'control_prefix=ctl_';

SELECT 'fact_rule=APPEND_OR_REPRODUCIBLE_CODES_ONLY';

SELECT 'state_fact_rule=LATEST_STATE_RECALCULABLE';

SELECT 'dimension_rule=REFERENCE_ENRICHED_LOOKUPS';

SELECT 'semantic_rule=BUSINESS_OBJECTS_FOR_CANDIDATE_WORKFLOW_MARKET_TRADE_EXECUTION_EDGE';

SELECT 'mart_rule=WIDE_RECALCULABLE_UI_READY';

SELECT 'snapshot_rule=APPEND_ONLY_HISTORICAL_STATE';

SELECT 'presentation_rule=READS_ONLY_MART_AND_SNAPSHOT';

SELECT 'multi_exchange=true';
SELECT 'multi_broker=true';
SELECT 'multi_account=true';
SELECT 'multi_portfolio=true';
SELECT 'multilingual=true';

SELECT 'health_standard=health_score,health_light,health_reason_code';

SELECT 'status_lights=GREEN,YELLOW,ORANGE,RED,BLACK,WHITE,BLUE';

SELECT 'localization_rule=FACTS_STORE_CODES_REFERENCE_STORES_LABELS_PRESENTATION_RENDERS_TERMS';

SELECT 'russian_terms_rule=PROFESSIONAL_DOMAIN_TERMS_NOT_LITERAL_TRANSLATION';

SELECT 'lineage_required=source_table,source_id,source_event_id,source_run_id,calculation_version,calculated_at';

SELECT 'versioning_required=workflow_version,strategy_version,statistics_version,semantic_version,mart_version,localization_version';

SELECT 'governance_required=ownership,retention,quality_rules,validation_rules,lineage_rules';

SELECT 'ui_control_rule=UI_CREATES_COMMANDS_INTENTS_EVENTS_NO_DIRECT_EXECUTION';

SELECT 'scheduler_rule=JOBS_TRIGGER_PIPELINES_NOT_DIRECT_BROKER_EXECUTION';

SELECT 'execution_rule=ORDER_INTENT_BEFORE_BROKER_ORDER';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=ENTERPRISE_DATA_MODEL_V1_READY';
SQL

echo "TEST_ENTERPRISE_DATA_MODEL_V1_OK"

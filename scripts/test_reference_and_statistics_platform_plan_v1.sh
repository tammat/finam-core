#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_REFERENCE_AND_STATISTICS_PLATFORM_PLAN_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'plan_block_1=REFERENCE_PLATFORM_ENGINE_V1';
SELECT 'reference_scope=brokers,exchanges,markets,instruments,aliases,contracts,strategies,stages,statuses,reasons,asset_classes,sessions,metrics,status_lights,localization,ui_sections,ui_actions';

SELECT 'plan_block_2=WORKFLOW_STATISTICS_DATASET_V1';
SELECT 'workflow_stats_scope=stage_facts,transition_facts,candidate_lifecycle,workflow_quality,workflow_health';

SELECT 'plan_block_3=MARKET_STATISTICS_DATASET_V1';
SELECT 'market_stats_scope=bar_quality,staleness,missing_bars,volatility_regime,liquidity,session_quality';

SELECT 'plan_block_4=TRADE_STATISTICS_DATASET_V1';
SELECT 'trade_stats_scope=signals,intents,orders,fills,trades,positions,commission,slippage,conversion';

SELECT 'plan_block_5=EDGE_STATISTICS_DATASET_V1';
SELECT 'edge_stats_scope=expectancy,profit_factor,winrate,drawdown,stability,oos,temporal_concentration,regime_dependency';

SELECT 'plan_block_6=UNIFIED_DASHBOARD_MART_V1';
SELECT 'mart_scope=candidate,market,workflow,execution,edge,health,traffic_lights,localized_labels';

SELECT 'plan_block_7=CONTROL_UI_COMMAND_MODEL_V1';
SELECT 'control_ui_scope=commands,approvals,audit,rbac,no_direct_execution';

SELECT 'canonical_id_policy=broker_id,exchange_id,market_code,instrument_id,strategy_code,stage_code,status_code,reason_code,metric_code';

SELECT 'fact_policy=STORE_CODES_ONLY';

SELECT 'presentation_policy=LOCALIZE_FROM_REFERENCE_PLATFORM';

SELECT 'russian_terminology_policy=PROFESSIONAL_DOMAIN_NATIVE_TERMS_AND_ABBREVIATIONS';

SELECT 'health_policy=EVERY_MAJOR_ENTITY_HAS_health_score_health_light_health_reason_code';

SELECT 'lineage_policy=source_table,source_id,calculation_version,calculated_at';

SELECT 'versioning_policy=workflow_version,strategy_version,statistics_version,mart_version,localization_version';

SELECT 'implementation_order=REFERENCE_PLATFORM_ENGINE_V1->WORKFLOW_STATISTICS_DATASET_V1->MARKET_STATISTICS_DATASET_V1->TRADE_STATISTICS_DATASET_V1->EDGE_STATISTICS_DATASET_V1->UNIFIED_DASHBOARD_MART_V1->CONTROL_UI_COMMAND_MODEL_V1';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=REFERENCE_AND_STATISTICS_PLATFORM_PLAN_V1_READY';
SQL

echo "TEST_REFERENCE_AND_STATISTICS_PLATFORM_PLAN_V1_OK"

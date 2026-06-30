#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_STATISTICS_INVENTORY_SCHEMA_V1 ==="

echo "catalog_name=ANALYTICS_ASSET_CATALOG_V1"
echo "catalog_role=PLATFORM_SELF_KNOWLEDGE"
echo "inventory_scope=ENTIRE_PLATFORM"

echo "domains=REFERENCE,WORKFLOW,MARKET,TRADE,EXECUTION,RISK,PORTFOLIO,RESEARCH,EDGE,PRESENTATION,SYSTEM,AI,FEATURES,MODELS"
echo "categories=TABLE,VIEW,MATERIALIZED_VIEW,FUNCTION,PIPELINE,BUILDER,SERVICE,SCRIPT,DASHBOARD,API,TELEGRAM,SYSTEMD,REPORT,INDICATOR,FEATURE,MODEL,EXPERIMENT,OPTIMIZER,AI_AGENT"

echo "warehouse_layers=LEGACY,REFERENCE,RAW,QUALITY,NORMALIZED,EVENT_FACT,STATE_FACT,DIMENSION,SEMANTIC,MART,SNAPSHOT,PRESENTATION"
echo "business_value=CRITICAL,HIGH,MEDIUM,LOW,EXPERIMENTAL"
echo "criticality=PLATFORM_CORE,BUSINESS_CRITICAL,IMPORTANT,OPTIONAL,EXPERIMENTAL"
echo "lifecycle=ACTIVE,FROZEN,REVIEW,LEGACY,DEPRECATED"
echo "evidence_level=PRODUCTION,VALIDATED,RESEARCH,EXPERIMENT,OBSOLETE"
echo "verification_status=NOT_VERIFIED,VERIFIED,REVIEW_REQUIRED"

echo "migration_decision=WAREHOUSE_NATIVE,LEGACY_KEEP,LEGACY_MIGRATE,LEGACY_MERGE,LEGACY_REPLACE,LEGACY_DEPRECATE,LEGACY_DELETE"
echo "cutover_status=NOT_PLANNED,PLANNED,DUAL_RUN,VALIDATED,SWITCHED,LEGACY_DISABLED"
echo "retention_policy=KEEP_FOREVER,KEEP_UNTIL_MIGRATED,ARCHIVE,DELETE_AFTER_VALIDATION"

echo "source_of_truth_fields=source_system,source_type,source_priority,source_of_truth,direct_source_available,direct_source_connector,legacy_dependency,replacement_source,migration_path,deprecation_condition"
echo "lineage_fields=upstream_objects,downstream_objects,parent_objects,child_objects,source_table,source_id,calculation_version,calculated_at"
echo "impact_fields=consumers,source_objects,target_objects,dependencies,successor,can_be_deleted,delete_after"

echo "ai_layer=AI_INTELLIGENCE_LAYER_V1"
echo "ai_roles=ANALYST,RANKER,EXPLAINER,OPTIMIZER,ANOMALY_DETECTOR,MARKET_SCANNER,CANDIDATE_REVIEWER"
echo "ai_policy=AI_RECOMMENDS_ONLY_NO_DIRECT_EXECUTION"
echo "ai_fields=ai_enabled,ai_role,ai_input_objects,ai_output_objects,ai_confidence,ai_explanation,ai_recommendation_type,ai_approval_required,human_review_required"

echo "feature_model_platform=FEATURE_AND_MODEL_PLATFORM_V1"
echo "indicator_classes=TREND,MOMENTUM,VOLATILITY,VOLUME,LIQUIDITY,SPREAD,ORDER_FLOW,SESSION,REGIME,CORRELATION,RISK"
echo "model_classes=STATISTICAL,MATHEMATICAL,ML,AI_ASSISTED,RULE_BASED,ENSEMBLE,REGIME_MODEL,ANOMALY_MODEL,OPTIMIZATION_MODEL"
echo "model_governance=MODEL_GOVERNANCE_V1"
echo "feature_lineage=FEATURE_LINEAGE_V1"

echo "analysis_methods=REGRESSION,CORRELATION,CLUSTERING,VOLATILITY_MODELS,SEASONALITY,WALK_FORWARD,MONTE_CARLO,BOOTSTRAP,BAYESIAN_UPDATE,STABILITY,DRAWDOWN,FACTOR_ANALYSIS,FEATURE_IMPORTANCE,DRIFT_DETECTION"

echo "market_movers=MARKET_MOVERS_ANALYTICS_V1"
echo "market_movers_scope=TOP_GAINERS,TOP_LOSERS,TOP_VOLUME,ANOMALIES,RESEARCH_CANDIDATES"

echo "rules=NO_NAMELESS_OBJECTS,SOURCE_OF_TRUTH_REQUIRED,LINEAGE_REQUIRED,AI_NO_DIRECT_ORDERS,MODEL_NO_DIRECT_EXECUTION,OPTIMIZER_NO_LIVE_CHANGE_WITHOUT_APPROVAL"
echo "knowledge_coverage_metrics=objects_cataloged,source_of_truth_coverage,lineage_coverage,migration_coverage,legacy_elimination"

echo "db_update=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=STATISTICS_INVENTORY_SCHEMA_V1_READY"
echo "TEST_STATISTICS_INVENTORY_SCHEMA_V1_OK"

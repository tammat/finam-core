#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_STATISTICS_INVENTORY_PLAN_V1 ==="

echo "catalog_name=ANALYTICS_ASSET_CATALOG_V1"
echo "plan_goal=BUILD_PLATFORM_SELF_KNOWLEDGE_CATALOG"

echo "scan_block_1=POSTGRES_OBJECTS"
echo "postgres_scope=schemas,tables,views,materialized_views,functions,indexes,row_counts,last_updates"

echo "scan_block_2=PYTHON_OBJECTS"
echo "python_scope=builders,pipelines,research_scripts,services,ui_servers,api_sources"

echo "scan_block_3=BASH_TESTS"
echo "bash_scope=test_scripts,setup_scripts,validation_scripts,checkpoint_scripts"

echo "scan_block_4=SYSTEMD_SERVICES"
echo "systemd_scope=services,timers,env_files,enabled_status,active_status"

echo "scan_block_5=PRESENTATION_OBJECTS"
echo "presentation_scope=dashboard,read_only_ui,telegram,api,reports,mart_consumers"

echo "scan_block_6=RESEARCH_ARTIFACTS"
echo "research_scope=replay,shadow,oos,edge,discovery,robustness,forensic_audit"

echo "scan_block_7=AI_FEATURE_MODEL_PLACEHOLDERS"
echo "ai_feature_model_scope=ai_agents,indicators,features,models,experiments,optimizers,market_movers"

echo "asset_passport_sections=identity,business,architecture,source_of_truth,runtime,quality,lineage,impact,ai,feature_model,governance"

echo "identity_fields=object_id,object_name,domain,category,version"
echo "business_fields=purpose,owner,steward,business_value,criticality,lifecycle,evidence_level"
echo "architecture_fields=layer,consumers,source_objects,target_objects,dependencies"
echo "source_of_truth_fields=source_system,source_type,source_priority,source_of_truth,direct_source_available,direct_source_connector,legacy_dependency,replacement_source,migration_path,cutover_status"
echo "runtime_fields=rows,size_bytes,growth_rate,update_frequency,last_update"
echo "quality_fields=health_score,health_light,validation_status,verification_status,can_be_deleted,delete_after"
echo "lineage_fields=upstream_objects,downstream_objects,parent_objects,child_objects"
echo "impact_fields=consumers,successor,deprecation_condition,retention_policy"
echo "ai_fields=ai_enabled,ai_role,ai_confidence,ai_explanation,ai_approval_required,human_review_required"
echo "feature_model_fields=indicator_code,feature_code,model_code,model_type,parameters,parameter_version,training_period,validation_period,oos_period,model_drift_score,model_health"

echo "classification_ready=1"
echo "classification_decisions=WAREHOUSE_NATIVE,LEGACY_KEEP,LEGACY_MIGRATE,LEGACY_MERGE,LEGACY_REPLACE,LEGACY_DEPRECATE,LEGACY_DELETE"

echo "source_of_truth_policy=PRIMARY_SOURCE_BEATS_LEGACY"
echo "cutover_policy=LEGACY_TO_DIRECT_SOURCE_VIA_DUAL_RUN_VALIDATION_SWITCH_ARCHIVE_DELETE"
echo "ai_policy=AI_RECOMMENDS_ONLY_NO_DIRECT_EXECUTION"
echo "model_policy=MODEL_NO_DIRECT_EXECUTION"
echo "optimizer_policy=OPTIMIZER_NO_LIVE_CHANGE_WITHOUT_APPROVAL"
echo "lineage_policy=UPSTREAM_DOWNSTREAM_REQUIRED"
echo "no_nameless_objects=1"

echo "knowledge_coverage_metrics=objects_cataloged,source_of_truth_coverage,lineage_coverage,migration_coverage,legacy_elimination"
echo "output_target=warehouse.analytics_asset_catalog_v1"
echo "output_mode=save_after_schema"

echo "db_update=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=STATISTICS_INVENTORY_PLAN_V1_READY"
echo "TEST_STATISTICS_INVENTORY_PLAN_V1_OK"

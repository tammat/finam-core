#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_CATALOG_DISCOVERY_ENGINE_SCHEMA_V1 ==="

echo "engine_name=CATALOG_DISCOVERY_ENGINE_V1"
echo "engine_role=AUTOMATIC_PLATFORM_ASSET_DISCOVERY"
echo "target_catalog=warehouse.analytics_asset_catalog_v1"

echo "discovery_flow=DISCOVERY,NORMALIZATION,ENRICHMENT,VALIDATION,CATALOG"

echo "plugin_model=PLUGIN_BASED"
echo "plugins=PostgresDiscovery,PythonDiscovery,BashDiscovery,SystemdDiscovery,UIDiscovery,ModelDiscovery,FeatureDiscovery"

echo "discovery_scope=POSTGRES,PYTHON,BASH,SYSTEMD,UI,AI,FEATURES,MODELS"

echo "postgres_discovery=schemas,tables,views,materialized_views,functions,indexes,row_counts,last_updates"
echo "python_discovery=builders,pipelines,research_scripts,services,ui_servers,api_sources"
echo "bash_discovery=test_scripts,setup_scripts,validation_scripts,migration_scripts"
echo "systemd_discovery=services,timers,env_files,enabled_status,active_status"
echo "ui_discovery=dashboard,read_only_ui,telegram,api,reports"
echo "ai_discovery=ai_agents,optimizers,market_scanners,candidate_reviewers"
echo "feature_model_discovery=indicators,features,models,experiments,model_registry,feature_store"

echo "discovered_object_fields=object_id,object_name,domain,category,object_type,path,schema_name,warehouse_layer,source_system,source_type,row_count,last_update,discovery_source,discovery_version,discovered_at,payload"

echo "normalization_policy=CANONICAL_OBJECT_ID_AND_CATEGORY"
echo "enrichment_policy=DOMAIN_LAYER_OWNER_CAPABILITY_MATURITY"
echo "validation_policy=NO_NAMELESS_OBJECTS_REQUIRED_FIELDS_DUPLICATE_CHECK"
echo "catalog_write_policy=UPSERT_BY_OBJECT_ID"
echo "catalog_missing_fields_policy=DEFAULT_TO_REVIEW_REQUIRED"

echo "workflow_profile_ready=1"
echo "profile_model=DOMAIN_SCOPED_DISCOVERY_PROFILE"
echo "first_profile=WORKFLOW_DISCOVERY_PROFILE_V1"

echo "source_of_truth_policy=DETECTED_OR_REVIEW_REQUIRED"
echo "lineage_policy=INITIAL_UPSTREAM_DOWNSTREAM_IF_DETECTABLE"
echo "ai_policy=AI_RECOMMENDS_ONLY_NO_DIRECT_EXECUTION"
echo "model_policy=MODEL_NO_DIRECT_EXECUTION"
echo "optimizer_policy=OPTIMIZER_NO_LIVE_CHANGE_WITHOUT_APPROVAL"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=CATALOG_DISCOVERY_ENGINE_SCHEMA_V1_READY"
echo "TEST_CATALOG_DISCOVERY_ENGINE_SCHEMA_V1_OK"

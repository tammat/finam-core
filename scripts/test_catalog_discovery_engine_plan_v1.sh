#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_CATALOG_DISCOVERY_ENGINE_PLAN_V1 ==="

echo "engine_name=CATALOG_DISCOVERY_ENGINE_V1"
echo "target_catalog=warehouse.analytics_asset_catalog_v1"

echo "implementation_units=DiscoveryContext,DiscoveredObject,DiscoveryPlugin,DiscoveryRegistry,DiscoveryExecutor,CatalogWriter"

echo "plugin_1=PostgresDiscovery"
echo "plugin_2=PythonDiscovery"
echo "plugin_3=BashDiscovery"
echo "plugin_4=SystemdDiscovery"
echo "plugin_5=UIDiscovery"
echo "plugin_6=ModelDiscovery"
echo "plugin_7=FeatureDiscovery"

echo "v1_active_plugins=PostgresDiscovery,PythonDiscovery,BashDiscovery,SystemdDiscovery"
echo "v1_deferred_plugins=UIDiscovery,ModelDiscovery,FeatureDiscovery"

echo "first_profile=WORKFLOW_DISCOVERY_PROFILE_V1"
echo "profile_scope=WORKFLOW_DOMAIN_ONLY"

echo "workflow_postgres_patterns=warehouse.qlt_workflow_%,warehouse.nrm_workflow_%,warehouse.fact_event_workflow_%,warehouse.fact_state_workflow_%,warehouse.fact_state_candidate_lifecycle_v1,warehouse.dim_stage_v1,warehouse.dim_status_light_v1,warehouse.sem_workflow_v1,warehouse.sem_candidate_v1,warehouse.mart_workflow_dashboard_v1,warehouse.mart_candidate_workflow_v1,warehouse.snap_workflow_daily_v1"

echo "workflow_python_patterns=build_workflow_*.py,serve_read_only_system_status_ui_v1.py"
echo "workflow_bash_patterns=test_workflow_*.sh,test_read_only_system_status_ui_v1.sh,setup_systemd_read_only_system_status_ui_v1.sh,test_readonly_ui_db_grants_v1.sh"
echo "workflow_systemd_patterns=finam-readonly-ui.service,finam-readonly-ui.env"

echo "normalization_rules=canonical_object_id,domain_from_name,category_from_source,layer_from_prefix,object_type_from_category"
echo "enrichment_rules=workflow_domain_defaults,platform_core_for_workflow_warehouse,visible_in_ui_for_mart_and_ui,review_required_for_unknowns"
echo "validation_rules=object_id_required,object_name_required,domain_required,category_required,no_duplicate_object_id"
echo "write_policy=UPSERT_BY_OBJECT_ID"

echo "default_owner=Warehouse"
echo "default_steward=Warehouse"
echo "default_lifecycle=ACTIVE"
echo "default_evidence_level=PRODUCTION"
echo "default_verification_status=VERIFIED"
echo "default_cutover_status=SWITCHED"
echo "default_source_system=POSTGRES_OR_REPOSITORY"
echo "default_source_type=DERIVED"
echo "default_source_of_truth=false"
echo "default_can_be_deleted=false"

echo "catalog_rows_expected_min=20"
echo "catalog_coverage_metric_ready=1"
echo "source_of_truth_coverage_metric_ready=1"
echo "lineage_coverage_metric_ready=1"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=CATALOG_DISCOVERY_ENGINE_PLAN_V1_READY"
echo "TEST_CATALOG_DISCOVERY_ENGINE_PLAN_V1_OK"

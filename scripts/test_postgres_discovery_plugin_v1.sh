#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_POSTGRES_DISCOVERY_PLUGIN_V1 ==="

PYTHONPATH=src src/scripts/research/build_postgres_discovery_plugin_v1.py \
  | tee /tmp/postgres_discovery_plugin_v1.out

grep -q "POSTGRES_DISCOVERY_PLUGIN_V1" /tmp/postgres_discovery_plugin_v1.out
grep -q "profile=WORKFLOW_DISCOVERY_PROFILE_V1" /tmp/postgres_discovery_plugin_v1.out
grep -q "domain=WORKFLOW" /tmp/postgres_discovery_plugin_v1.out
grep -q "discovered_object=postgres:warehouse.qlt_workflow_event_v1" /tmp/postgres_discovery_plugin_v1.out
grep -q "discovered_object=postgres:warehouse.nrm_workflow_event_v1" /tmp/postgres_discovery_plugin_v1.out
grep -q "discovered_object=postgres:warehouse.fact_event_workflow_stage_v1" /tmp/postgres_discovery_plugin_v1.out
grep -q "discovered_object=postgres:warehouse.fact_state_candidate_lifecycle_v1" /tmp/postgres_discovery_plugin_v1.out
grep -q "discovered_object=postgres:warehouse.sem_candidate_v1" /tmp/postgres_discovery_plugin_v1.out
grep -q "discovered_object=postgres:warehouse.mart_candidate_workflow_v1" /tmp/postgres_discovery_plugin_v1.out
grep -q "discovered_object=postgres:warehouse.snap_workflow_daily_v1" /tmp/postgres_discovery_plugin_v1.out
grep -q "plugin_model=PLUGIN_BASED" /tmp/postgres_discovery_plugin_v1.out
grep -q "normalization_ready=1" /tmp/postgres_discovery_plugin_v1.out
grep -q "catalog_write_deferred=1" /tmp/postgres_discovery_plugin_v1.out
grep -q "runtime_changed=0" /tmp/postgres_discovery_plugin_v1.out
grep -q "execution_changed=0" /tmp/postgres_discovery_plugin_v1.out
grep -q "orders_changed=0" /tmp/postgres_discovery_plugin_v1.out
grep -q "fills_changed=0" /tmp/postgres_discovery_plugin_v1.out
grep -q "micro_live_allowed=0" /tmp/postgres_discovery_plugin_v1.out
grep -q "VERDICT=POSTGRES_DISCOVERY_PLUGIN_V1_READY" /tmp/postgres_discovery_plugin_v1.out

echo "TEST_POSTGRES_DISCOVERY_PLUGIN_V1_OK"

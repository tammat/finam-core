#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DISCOVERY_EXECUTOR_V1 ==="

PYTHONPATH=src src/scripts/research/build_discovery_executor_v1.py \
  | tee /tmp/discovery_executor_v1.out

grep -q "DISCOVERY_EXECUTOR_V1" /tmp/discovery_executor_v1.out
grep -q "profile=WORKFLOW_DISCOVERY_PROFILE_V1" /tmp/discovery_executor_v1.out
grep -q "plugins=PostgresDiscovery,PythonDiscovery" /tmp/discovery_executor_v1.out
grep -q "source_count=PostgresDiscovery:" /tmp/discovery_executor_v1.out
grep -q "source_count=PythonDiscovery:" /tmp/discovery_executor_v1.out
grep -q "executor_object=postgres:warehouse.qlt_workflow_event_v1" /tmp/discovery_executor_v1.out
grep -q "executor_object=postgres:warehouse.sem_candidate_v1" /tmp/discovery_executor_v1.out
grep -q "executor_object=postgres:warehouse.mart_candidate_workflow_v1" /tmp/discovery_executor_v1.out
grep -q "executor_object=python:src/scripts/research/build_workflow_semantic_builder_v1.py" /tmp/discovery_executor_v1.out
grep -q "executor_object=python:src/scripts/research/serve_read_only_system_status_ui_v1.py" /tmp/discovery_executor_v1.out
grep -q "executor_policy=DEDUP_BY_OBJECT_ID" /tmp/discovery_executor_v1.out
grep -q "catalog_write_deferred=1" /tmp/discovery_executor_v1.out
grep -q "runtime_changed=0" /tmp/discovery_executor_v1.out
grep -q "execution_changed=0" /tmp/discovery_executor_v1.out
grep -q "orders_changed=0" /tmp/discovery_executor_v1.out
grep -q "fills_changed=0" /tmp/discovery_executor_v1.out
grep -q "micro_live_allowed=0" /tmp/discovery_executor_v1.out
grep -q "VERDICT=DISCOVERY_EXECUTOR_V1_READY" /tmp/discovery_executor_v1.out

echo "TEST_DISCOVERY_EXECUTOR_V1_OK"

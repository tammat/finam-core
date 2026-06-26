#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PYTHON_DISCOVERY_PLUGIN_V1 ==="

PYTHONPATH=src src/scripts/research/build_python_discovery_plugin_v1.py \
  | tee /tmp/python_discovery_plugin_v1.out

grep -q "PYTHON_DISCOVERY_PLUGIN_V1" /tmp/python_discovery_plugin_v1.out
grep -q "profile=WORKFLOW_DISCOVERY_PROFILE_V1" /tmp/python_discovery_plugin_v1.out
grep -q "domain=WORKFLOW" /tmp/python_discovery_plugin_v1.out
grep -q "discovered_object=python:src/scripts/research/build_workflow_semantic_builder_v1.py" /tmp/python_discovery_plugin_v1.out
grep -q "discovered_object=python:src/scripts/research/build_workflow_mart_builder_v1.py" /tmp/python_discovery_plugin_v1.out
grep -q "discovered_object=python:src/scripts/research/build_workflow_snapshot_builder_v1.py" /tmp/python_discovery_plugin_v1.out
grep -q "discovered_object=python:src/scripts/research/build_workflow_warehouse_validation_v1.py" /tmp/python_discovery_plugin_v1.out
grep -q "discovered_object=python:src/scripts/research/serve_read_only_system_status_ui_v1.py" /tmp/python_discovery_plugin_v1.out
grep -q "discovery_source=PythonDiscovery" /tmp/python_discovery_plugin_v1.out
grep -q "catalog_write_deferred=1" /tmp/python_discovery_plugin_v1.out
grep -q "runtime_changed=0" /tmp/python_discovery_plugin_v1.out
grep -q "execution_changed=0" /tmp/python_discovery_plugin_v1.out
grep -q "orders_changed=0" /tmp/python_discovery_plugin_v1.out
grep -q "fills_changed=0" /tmp/python_discovery_plugin_v1.out
grep -q "micro_live_allowed=0" /tmp/python_discovery_plugin_v1.out
grep -q "VERDICT=PYTHON_DISCOVERY_PLUGIN_V1_READY" /tmp/python_discovery_plugin_v1.out

echo "TEST_PYTHON_DISCOVERY_PLUGIN_V1_OK"

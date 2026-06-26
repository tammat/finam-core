#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_BASH_DISCOVERY_PLUGIN_V1 ==="

PYTHONPATH=src src/scripts/research/build_bash_discovery_plugin_v1.py \
  | tee /tmp/bash_discovery_plugin_v1.out

grep -q "BASH_DISCOVERY_PLUGIN_V1" /tmp/bash_discovery_plugin_v1.out
grep -q "profile=WORKFLOW_DISCOVERY_PROFILE_V1" /tmp/bash_discovery_plugin_v1.out
grep -q "domain=WORKFLOW" /tmp/bash_discovery_plugin_v1.out
grep -q "discovered_object=bash:scripts/test_workflow_discovery_profile_v1.sh" /tmp/bash_discovery_plugin_v1.out
grep -q "discovered_object=bash:scripts/test_catalog_discovery_validation_v1.sh" /tmp/bash_discovery_plugin_v1.out
grep -q "discovered_object=bash:scripts/test_read_only_system_status_ui_v1.sh" /tmp/bash_discovery_plugin_v1.out
grep -q "discovery_source=BashDiscovery" /tmp/bash_discovery_plugin_v1.out
grep -q "catalog_write_deferred=1" /tmp/bash_discovery_plugin_v1.out
grep -q "runtime_changed=0" /tmp/bash_discovery_plugin_v1.out
grep -q "execution_changed=0" /tmp/bash_discovery_plugin_v1.out
grep -q "orders_changed=0" /tmp/bash_discovery_plugin_v1.out
grep -q "fills_changed=0" /tmp/bash_discovery_plugin_v1.out
grep -q "micro_live_allowed=0" /tmp/bash_discovery_plugin_v1.out
grep -q "VERDICT=BASH_DISCOVERY_PLUGIN_V1_READY" /tmp/bash_discovery_plugin_v1.out

echo "TEST_BASH_DISCOVERY_PLUGIN_V1_OK"

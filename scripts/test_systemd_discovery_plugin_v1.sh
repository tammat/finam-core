#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_SYSTEMD_DISCOVERY_PLUGIN_V1 ==="

PYTHONPATH=src src/scripts/research/build_systemd_discovery_plugin_v1.py \
  | tee /tmp/systemd_discovery_plugin_v1.out

grep -q "SYSTEMD_DISCOVERY_PLUGIN_V1" /tmp/systemd_discovery_plugin_v1.out
grep -q "profile=WORKFLOW_DISCOVERY_PROFILE_V1" /tmp/systemd_discovery_plugin_v1.out
grep -q "domain=WORKFLOW" /tmp/systemd_discovery_plugin_v1.out
grep -q "objects_discovered=" /tmp/systemd_discovery_plugin_v1.out
grep -q "service_objects=" /tmp/systemd_discovery_plugin_v1.out
grep -q "env_objects=" /tmp/systemd_discovery_plugin_v1.out
grep -q "discovered_object=systemd:systemd/finam-readonly-ui.service" /tmp/systemd_discovery_plugin_v1.out
grep -q "discovered_object=systemd:systemd/finam-readonly-ui.env" /tmp/systemd_discovery_plugin_v1.out
grep -q "discovery_source=SystemdDiscovery" /tmp/systemd_discovery_plugin_v1.out
grep -q "catalog_write_deferred=1" /tmp/systemd_discovery_plugin_v1.out
grep -q "runtime_changed=0" /tmp/systemd_discovery_plugin_v1.out
grep -q "execution_changed=0" /tmp/systemd_discovery_plugin_v1.out
grep -q "orders_changed=0" /tmp/systemd_discovery_plugin_v1.out
grep -q "fills_changed=0" /tmp/systemd_discovery_plugin_v1.out
grep -q "micro_live_allowed=0" /tmp/systemd_discovery_plugin_v1.out
grep -q "VERDICT=SYSTEMD_DISCOVERY_PLUGIN_V1_READY" /tmp/systemd_discovery_plugin_v1.out

echo "TEST_SYSTEMD_DISCOVERY_PLUGIN_V1_OK"

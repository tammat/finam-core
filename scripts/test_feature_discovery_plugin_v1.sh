#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FEATURE_DISCOVERY_PLUGIN_V1 ==="

PYTHONPATH=src src/scripts/research/build_feature_discovery_plugin_v1.py \
  | tee /tmp/feature_discovery_plugin_v1.out

grep -q "FEATURE_DISCOVERY_PLUGIN_V1" /tmp/feature_discovery_plugin_v1.out
grep -q "profile=FEATURE_DISCOVERY_PROFILE_V1" /tmp/feature_discovery_plugin_v1.out
grep -q "domain=FEATURES" /tmp/feature_discovery_plugin_v1.out
grep -q "objects_discovered=" /tmp/feature_discovery_plugin_v1.out
grep -q "discovery_source=FeatureDiscovery" /tmp/feature_discovery_plugin_v1.out
grep -q "catalog_write_deferred=1" /tmp/feature_discovery_plugin_v1.out
grep -q "ai_policy=AI_RECOMMENDS_ONLY_NO_DIRECT_EXECUTION" /tmp/feature_discovery_plugin_v1.out
grep -q "model_policy=MODEL_NO_DIRECT_EXECUTION" /tmp/feature_discovery_plugin_v1.out
grep -q "runtime_changed=0" /tmp/feature_discovery_plugin_v1.out
grep -q "execution_changed=0" /tmp/feature_discovery_plugin_v1.out
grep -q "orders_changed=0" /tmp/feature_discovery_plugin_v1.out
grep -q "fills_changed=0" /tmp/feature_discovery_plugin_v1.out
grep -q "micro_live_allowed=0" /tmp/feature_discovery_plugin_v1.out
grep -q "VERDICT=FEATURE_DISCOVERY_PLUGIN_V1_READY" /tmp/feature_discovery_plugin_v1.out

echo "TEST_FEATURE_DISCOVERY_PLUGIN_V1_OK"

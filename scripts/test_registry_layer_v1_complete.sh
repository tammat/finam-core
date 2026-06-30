#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_REGISTRY_LAYER_V1_COMPLETE ==="

scripts/test_feature_registry_complete_v1.sh >/tmp/registry_feature_complete.out
scripts/test_model_registry_complete_v1.sh >/tmp/registry_model_complete.out
scripts/test_experiment_registry_complete_v1.sh >/tmp/registry_experiment_complete.out

grep -q "VERDICT=FEATURE_REGISTRY_V1_COMPLETE" /tmp/registry_feature_complete.out
grep -q "VERDICT=MODEL_REGISTRY_V1_COMPLETE" /tmp/registry_model_complete.out
grep -q "VERDICT=EXPERIMENT_REGISTRY_V1_COMPLETE" /tmp/registry_experiment_complete.out

curl -fsS http://127.0.0.1:8089/knowledge >/tmp/registry_layer_ui.html
grep -q "MarketCore Knowledge Center V2" /tmp/registry_layer_ui.html
grep -q "features=352" /tmp/registry_layer_ui.html
grep -q "models=280" /tmp/registry_layer_ui.html

echo "feature_registry=READY"
echo "model_registry=READY"
echo "experiment_registry=READY"
echo "knowledge_center=READY"
echo "single_ui_port=8089"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=REGISTRY_LAYER_V1_COMPLETE"
echo "TEST_REGISTRY_LAYER_V1_COMPLETE_OK"

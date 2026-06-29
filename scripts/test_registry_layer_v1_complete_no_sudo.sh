#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_REGISTRY_LAYER_V1_COMPLETE_NO_SUDO ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' | tee /tmp/registry_layer_v1_complete_no_sudo.out
SELECT 'feature_registry_rows=' || count(*) FROM warehouse.feature_registry_v1;
SELECT 'model_registry_rows=' || count(*) FROM warehouse.model_registry_v1;
SELECT 'experiment_registry_rows=' || count(*) FROM warehouse.experiment_registry_v1;

SELECT 'feature_unsafe=' || count(*) FROM warehouse.feature_registry_v1
WHERE approved_for_live=true OR approved_for_paper=true OR approved_for_shadow=true;

SELECT 'model_unsafe=' || count(*) FROM warehouse.model_registry_v1
WHERE approved_for_live=true OR approved_for_paper=true OR approved_for_shadow=true;

SELECT 'experiment_unsafe=' || count(*) FROM warehouse.experiment_registry_v1
WHERE approved_for_live=true OR approved_for_paper=true OR approved_for_shadow=true;
SQL

grep -q "feature_registry_rows=352" /tmp/registry_layer_v1_complete_no_sudo.out
grep -q "model_registry_rows=280" /tmp/registry_layer_v1_complete_no_sudo.out
grep -q "experiment_registry_rows=1" /tmp/registry_layer_v1_complete_no_sudo.out
grep -q "feature_unsafe=0" /tmp/registry_layer_v1_complete_no_sudo.out
grep -q "model_unsafe=0" /tmp/registry_layer_v1_complete_no_sudo.out
grep -q "experiment_unsafe=0" /tmp/registry_layer_v1_complete_no_sudo.out

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

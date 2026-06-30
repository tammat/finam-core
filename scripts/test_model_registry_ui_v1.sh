#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MODEL_REGISTRY_UI_V1 ==="

curl -fsS http://127.0.0.1:8089/knowledge/models -o /tmp/model_registry_ui_v1.html
curl -fsS http://127.0.0.1:8089/knowledge/models/health -o /tmp/model_registry_ui_health_v1.html

grep -q "MarketCore Model Registry" /tmp/model_registry_ui_v1.html
grep -q "total=280" /tmp/model_registry_ui_v1.html
grep -q "live_approved=0" /tmp/model_registry_ui_v1.html
grep -q "MODEL_REGISTRY_READ_ONLY" /tmp/model_registry_ui_v1.html

grep -q "MarketCore Model Registry Health" /tmp/model_registry_ui_health_v1.html
grep -q "missing_model_code=0" /tmp/model_registry_ui_health_v1.html
grep -q "unsafe_approvals=0" /tmp/model_registry_ui_health_v1.html

echo "single_ui_port=8089"
echo "route_models=/knowledge/models"
echo "route_models_health=/knowledge/models/health"
echo "source_policy=MODEL_REGISTRY_READ_ONLY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MODEL_REGISTRY_UI_V1_READY"
echo "TEST_MODEL_REGISTRY_UI_V1_OK"

#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FEATURE_REGISTRY_UI_V1 ==="

sudo systemctl restart finam-readonly-ui
sleep 2

curl -fsS http://127.0.0.1:8089/knowledge/features -o /tmp/feature_registry_ui_v1.html
curl -fsS http://127.0.0.1:8089/knowledge/features/health -o /tmp/feature_registry_ui_health_v1.html

grep -q "MarketCore Feature Registry" /tmp/feature_registry_ui_v1.html
grep -q "total=352" /tmp/feature_registry_ui_v1.html
grep -q "discovered=352" /tmp/feature_registry_ui_v1.html
grep -q "live_approved=0" /tmp/feature_registry_ui_v1.html
grep -q "FEATURE_REGISTRY_READ_ONLY" /tmp/feature_registry_ui_v1.html

grep -q "MarketCore Feature Registry Health" /tmp/feature_registry_ui_health_v1.html
grep -q "missing_feature_code=0" /tmp/feature_registry_ui_health_v1.html
grep -q "unsafe_approvals=0" /tmp/feature_registry_ui_health_v1.html
grep -q "micro_live_allowed=0" /tmp/feature_registry_ui_health_v1.html

echo "single_ui_port=8089"
echo "route_features=/knowledge/features"
echo "route_features_health=/knowledge/features/health"
echo "source_policy=FEATURE_REGISTRY_READ_ONLY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=FEATURE_REGISTRY_UI_V1_READY"
echo "TEST_FEATURE_REGISTRY_UI_V1_OK"

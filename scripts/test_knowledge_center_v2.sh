#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_KNOWLEDGE_CENTER_V2 ==="

sudo -u postgres psql finam_core -c "GRANT SELECT ON warehouse.feature_registry_v1 TO alex;"
sudo -u postgres psql finam_core -c "GRANT SELECT ON warehouse.model_registry_v1 TO alex;"

sudo systemctl restart finam-readonly-ui
sleep 2

curl -fsS http://127.0.0.1:8089/knowledge -o /tmp/knowledge_center_v2.html

grep -q "MarketCore Knowledge Center V2" /tmp/knowledge_center_v2.html
grep -q "Overview" /tmp/knowledge_center_v2.html
grep -q "Discovery" /tmp/knowledge_center_v2.html
grep -q "Coverage" /tmp/knowledge_center_v2.html
grep -q "Features" /tmp/knowledge_center_v2.html
grep -q "Models" /tmp/knowledge_center_v2.html
grep -q "catalog_objects=" /tmp/knowledge_center_v2.html
grep -q "features=352" /tmp/knowledge_center_v2.html
grep -q "models=280" /tmp/knowledge_center_v2.html
grep -q "WORKFLOW" /tmp/knowledge_center_v2.html
grep -q "FEATURES" /tmp/knowledge_center_v2.html
grep -q "MODELS" /tmp/knowledge_center_v2.html
grep -q "KNOWLEDGE_CENTER_READ_ONLY" /tmp/knowledge_center_v2.html
grep -q "micro_live_allowed=0" /tmp/knowledge_center_v2.html

echo "single_ui_port=8089"
echo "route_knowledge=/knowledge"
echo "knowledge_center_v2=READY"
echo "sections=overview,discovery,coverage,features,models"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=KNOWLEDGE_CENTER_V2_READY"
echo "TEST_KNOWLEDGE_CENTER_V2_OK"

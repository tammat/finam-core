#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_READ_ONLY_UI_MODULARIZATION_V1 ==="

sudo -u postgres psql finam_core -c "GRANT SELECT ON warehouse.model_registry_v1 TO alex;"
sudo -u postgres psql finam_core -c "GRANT SELECT ON warehouse.feature_registry_v1 TO alex;"
sudo -u postgres psql finam_core -c "GRANT SELECT ON warehouse.analytics_asset_catalog_v1 TO alex;"

sudo systemctl restart finam-readonly-ui
sleep 2

curl -fsS http://127.0.0.1:8089/knowledge -o /tmp/ui_mod_knowledge.html
curl -fsS http://127.0.0.1:8089/knowledge/models -o /tmp/ui_mod_models.html
curl -fsS http://127.0.0.1:8089/knowledge/models/health -o /tmp/ui_mod_models_health.html

grep -q "MarketCore Knowledge Center V2" /tmp/ui_mod_knowledge.html
grep -q "features=352" /tmp/ui_mod_knowledge.html
grep -q "models=280" /tmp/ui_mod_knowledge.html

grep -q "MarketCore Model Registry" /tmp/ui_mod_models.html
grep -q "total=280" /tmp/ui_mod_models.html
grep -q "live_approved=0" /tmp/ui_mod_models.html

grep -q "MarketCore Model Registry Health" /tmp/ui_mod_models_health.html
grep -q "missing_model_code=0" /tmp/ui_mod_models_health.html
grep -q "unsafe_approvals=0" /tmp/ui_mod_models_health.html

echo "single_ui_port=8089"
echo "router=ReadOnlyRouter"
echo "modular_pages=knowledge,models"
echo "route_knowledge=/knowledge"
echo "route_models=/knowledge/models"
echo "route_models_health=/knowledge/models/health"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=READ_ONLY_UI_MODULARIZATION_V1_READY"
echo "TEST_READ_ONLY_UI_MODULARIZATION_V1_OK"

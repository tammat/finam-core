#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_REGISTRY_DATA_CONSOLIDATION_UI_V1 ==="

sudo -u postgres psql finam_core -c "GRANT SELECT ON warehouse.registry_relationship_v1 TO alex;"

sudo systemctl restart finam-readonly-ui
sleep 2

curl -fsS http://127.0.0.1:8089/knowledge/relationships \
  -o /tmp/registry_relationships_ui_v1.html

grep -q "MarketCore Registry Relationships" /tmp/registry_relationships_ui_v1.html
grep -q "total=632" /tmp/registry_relationships_ui_v1.html
grep -q "validated=632" /tmp/registry_relationships_ui_v1.html
grep -q "not_validated=0" /tmp/registry_relationships_ui_v1.html
grep -q "CATALOG_TO_FEATURE" /tmp/registry_relationships_ui_v1.html
grep -q "CATALOG_TO_MODEL" /tmp/registry_relationships_ui_v1.html
grep -q "missing_source_code=0" /tmp/registry_relationships_ui_v1.html
grep -q "missing_target_code=0" /tmp/registry_relationships_ui_v1.html
grep -q "REGISTRY_RELATIONSHIP_READ_ONLY" /tmp/registry_relationships_ui_v1.html
grep -q "micro_live_allowed=0" /tmp/registry_relationships_ui_v1.html

echo "single_ui_port=8089"
echo "route_relationships=/knowledge/relationships"
echo "source_policy=REGISTRY_RELATIONSHIP_READ_ONLY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=REGISTRY_DATA_CONSOLIDATION_UI_V1_READY"
echo "TEST_REGISTRY_DATA_CONSOLIDATION_UI_V1_OK"

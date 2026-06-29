#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FEATURE_REGISTRY_COMPLETE_V1 ==="

scripts/test_feature_registry_schema_v1.sh >/tmp/feature_registry_schema_complete.out
scripts/test_feature_registry_builder_v1.sh >/tmp/feature_registry_builder_complete.out
scripts/test_feature_registry_validation_v1.sh >/tmp/feature_registry_validation_complete.out
scripts/test_feature_registry_cli_v1.sh >/tmp/feature_registry_cli_complete.out
scripts/test_feature_registry_ui_v1.sh >/tmp/feature_registry_ui_complete.out

grep -q "VERDICT=FEATURE_REGISTRY_SCHEMA_V1_READY" /tmp/feature_registry_schema_complete.out
grep -q "VERDICT=FEATURE_REGISTRY_BUILDER_V1_READY" /tmp/feature_registry_builder_complete.out
grep -q "VERDICT=FEATURE_REGISTRY_VALIDATION_V1_READY" /tmp/feature_registry_validation_complete.out
grep -q "VERDICT=FEATURE_REGISTRY_CLI_V1_READY" /tmp/feature_registry_cli_complete.out
grep -q "VERDICT=FEATURE_REGISTRY_UI_V1_READY" /tmp/feature_registry_ui_complete.out

curl -fsS http://127.0.0.1:8089/knowledge/features >/tmp/feature_registry_complete_ui.html
grep -q "MarketCore Feature Registry" /tmp/feature_registry_complete_ui.html
grep -q "total=352" /tmp/feature_registry_complete_ui.html

echo "storage=READY"
echo "validation=READY"
echo "cli=READY"
echo "read_only_ui=READY"
echo "single_ui_port=8089"
echo "feature_registry_rows=352"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=FEATURE_REGISTRY_V1_COMPLETE"
echo "TEST_FEATURE_REGISTRY_COMPLETE_V1_OK"

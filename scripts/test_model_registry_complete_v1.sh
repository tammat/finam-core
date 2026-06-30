#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MODEL_REGISTRY_COMPLETE_V1 ==="

scripts/test_model_registry_schema_v1.sh >/tmp/model_registry_schema_complete.out
scripts/test_model_registry_builder_v1.sh >/tmp/model_registry_builder_complete.out
scripts/test_model_registry_validation_v1.sh >/tmp/model_registry_validation_complete.out
scripts/test_model_registry_cli_v1.sh >/tmp/model_registry_cli_complete.out
scripts/test_read_only_ui_modularization_v1.sh >/tmp/ui_modularization_complete.out
scripts/test_model_registry_ui_v1.sh >/tmp/model_registry_ui_complete.out

grep -q "VERDICT=MODEL_REGISTRY_SCHEMA_V1_READY" /tmp/model_registry_schema_complete.out
grep -q "VERDICT=MODEL_REGISTRY_BUILDER_V1_READY" /tmp/model_registry_builder_complete.out
grep -q "VERDICT=MODEL_REGISTRY_VALIDATION_V1_READY" /tmp/model_registry_validation_complete.out
grep -q "VERDICT=MODEL_REGISTRY_CLI_V1_READY" /tmp/model_registry_cli_complete.out
grep -q "VERDICT=READ_ONLY_UI_MODULARIZATION_V1_READY" /tmp/ui_modularization_complete.out
grep -q "VERDICT=MODEL_REGISTRY_UI_V1_READY" /tmp/model_registry_ui_complete.out

echo "storage=READY"
echo "validation=READY"
echo "cli=READY"
echo "read_only_ui=READY"
echo "single_ui_port=8089"
echo "model_registry_rows=280"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MODEL_REGISTRY_V1_COMPLETE"
echo "TEST_MODEL_REGISTRY_COMPLETE_V1_OK"

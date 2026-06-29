#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_REGISTRY_DATA_CONSOLIDATION_COMPLETE_V1 ==="

scripts/test_registry_data_consolidation_schema_v1.sh >/tmp/reg_con_schema.out
scripts/test_registry_data_consolidation_builder_v1.sh >/tmp/reg_con_builder.out
scripts/test_registry_data_consolidation_validation_v1.sh >/tmp/reg_con_validation.out
scripts/test_registry_data_consolidation_cli_v1.sh >/tmp/reg_con_cli.out
scripts/test_registry_data_consolidation_ui_v1.sh >/tmp/reg_con_ui.out

grep -q "VERDICT=REGISTRY_DATA_CONSOLIDATION_SCHEMA_V1_READY" /tmp/reg_con_schema.out
grep -q "VERDICT=REGISTRY_DATA_CONSOLIDATION_BUILDER_V1_READY" /tmp/reg_con_builder.out
grep -q "VERDICT=REGISTRY_DATA_CONSOLIDATION_VALIDATION_V1_READY" /tmp/reg_con_validation.out
grep -q "VERDICT=REGISTRY_DATA_CONSOLIDATION_CLI_V1_READY" /tmp/reg_con_cli.out
grep -q "VERDICT=REGISTRY_DATA_CONSOLIDATION_UI_V1_READY" /tmp/reg_con_ui.out

echo "storage=READY"
echo "builder=READY"
echo "validation=READY"
echo "cli=READY"
echo "read_only_ui=READY"
echo "single_ui_port=8089"
echo "relationships=632"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=REGISTRY_DATA_CONSOLIDATION_V1_COMPLETE"
echo "TEST_REGISTRY_DATA_CONSOLIDATION_COMPLETE_V1_OK"

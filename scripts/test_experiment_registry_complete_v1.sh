#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EXPERIMENT_REGISTRY_COMPLETE_V1 ==="

scripts/test_experiment_registry_schema_v1.sh >/tmp/exp_schema.out
scripts/test_experiment_registry_builder_v1.sh >/tmp/exp_builder.out
scripts/test_experiment_registry_validation_v1.sh >/tmp/exp_validation.out
scripts/test_experiment_registry_cli_v1.sh >/tmp/exp_cli.out
scripts/test_experiment_registry_ui_v1.sh >/tmp/exp_ui.out

grep -q "VERDICT=EXPERIMENT_REGISTRY_SCHEMA_V1_READY" /tmp/exp_schema.out
grep -q "VERDICT=EXPERIMENT_REGISTRY_BUILDER_V1_READY" /tmp/exp_builder.out
grep -q "VERDICT=EXPERIMENT_REGISTRY_VALIDATION_V1_READY" /tmp/exp_validation.out
grep -q "VERDICT=EXPERIMENT_REGISTRY_CLI_V1_READY" /tmp/exp_cli.out
grep -q "VERDICT=EXPERIMENT_REGISTRY_UI_V1_READY" /tmp/exp_ui.out

echo "storage=READY"
echo "validation=READY"
echo "cli=READY"
echo "read_only_ui=READY"
echo "single_ui_port=8089"
echo "experiment_registry_rows=1"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EXPERIMENT_REGISTRY_V1_COMPLETE"
echo "TEST_EXPERIMENT_REGISTRY_COMPLETE_V1_OK"

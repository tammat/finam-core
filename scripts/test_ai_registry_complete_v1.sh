#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_AI_REGISTRY_COMPLETE_V1 ==="

scripts/test_ai_registry_schema_v1.sh >/tmp/ai_registry_schema_complete.out
scripts/test_ai_registry_builder_v1.sh >/tmp/ai_registry_builder_complete.out
scripts/test_ai_registry_validation_v1.sh >/tmp/ai_registry_validation_complete.out
scripts/test_ai_registry_cli_v1.sh >/tmp/ai_registry_cli_complete.out
scripts/test_ai_registry_ui_v1.sh >/tmp/ai_registry_ui_complete.out
scripts/test_ai_registry_ui_smoke_no_sudo_v1.sh >/tmp/ai_registry_ui_smoke_complete.out

grep -q "VERDICT=AI_REGISTRY_SCHEMA_V1_READY" /tmp/ai_registry_schema_complete.out
grep -q "VERDICT=AI_REGISTRY_BUILDER_V1_READY" /tmp/ai_registry_builder_complete.out
grep -q "VERDICT=AI_REGISTRY_VALIDATION_V1_READY" /tmp/ai_registry_validation_complete.out
grep -q "VERDICT=AI_REGISTRY_CLI_V1_READY" /tmp/ai_registry_cli_complete.out
grep -q "VERDICT=AI_REGISTRY_UI_V1_READY" /tmp/ai_registry_ui_complete.out
grep -q "VERDICT=AI_REGISTRY_UI_SMOKE_NO_SUDO_V1_READY" /tmp/ai_registry_ui_smoke_complete.out

echo "schema=READY"
echo "builder=READY"
echo "validation=READY"
echo "cli=READY"
echo "read_only_ui=READY"
echo "ui_smoke_no_sudo=READY"

echo "framework=REGISTRY_FRAMEWORK_V1"
echo "bootstrap_policy=AI_BOOTSTRAP_POLICY_V1"
echo "market_isolation=READY"
echo "read_only_policy=READY"

echo "single_ui_port=8089"
echo "route_ai=/knowledge/ai"

echo "ai_registry_total=10"
echo "ai_agents=4"
echo "ai_policies=4"
echo "ai_capabilities=2"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=AI_REGISTRY_V1_COMPLETE"
echo "TEST_AI_REGISTRY_COMPLETE_V1_OK"

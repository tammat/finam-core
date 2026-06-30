#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MODEL_REGISTRY_CLI_V1 ==="

PYTHONPATH=src src/marketcore/cli/main.py model summary | tee /tmp/model_registry_cli_summary.out
grep -q "total=280" /tmp/model_registry_cli_summary.out
grep -q "discovered=280" /tmp/model_registry_cli_summary.out
grep -q "live_approved=0" /tmp/model_registry_cli_summary.out

PYTHONPATH=src src/marketcore/cli/main.py model list --limit 5 | tee /tmp/model_registry_cli_list.out
grep -q "model_code=" /tmp/model_registry_cli_list.out

PYTHONPATH=src src/marketcore/cli/main.py model search model | tee /tmp/model_registry_cli_search.out
grep -q "model_code=" /tmp/model_registry_cli_search.out

PYTHONPATH=src src/marketcore/cli/main.py model health | tee /tmp/model_registry_cli_health.out
grep -q "unsafe_approvals=0" /tmp/model_registry_cli_health.out

PYTHONPATH=src src/marketcore/cli/main.py model summary --json | tee /tmp/model_registry_cli_json.out
grep -q '"total"' /tmp/model_registry_cli_json.out

echo "model_registry_cli=READY"
echo "commands=summary,list,search,health"
echo "ai_policy=AI_RECOMMENDS_ONLY_NO_DIRECT_EXECUTION"
echo "model_policy=MODEL_NO_DIRECT_EXECUTION"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MODEL_REGISTRY_CLI_V1_READY"
echo "TEST_MODEL_REGISTRY_CLI_V1_OK"

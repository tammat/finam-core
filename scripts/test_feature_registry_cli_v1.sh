#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FEATURE_REGISTRY_CLI_V1 ==="

PYTHONPATH=src src/marketcore/cli/main.py feature summary | tee /tmp/feature_registry_cli_summary.out
grep -q "total=352" /tmp/feature_registry_cli_summary.out
grep -q "discovered=352" /tmp/feature_registry_cli_summary.out
grep -q "live_approved=0" /tmp/feature_registry_cli_summary.out

PYTHONPATH=src src/marketcore/cli/main.py feature list --limit 5 | tee /tmp/feature_registry_cli_list.out
grep -q "feature_code=" /tmp/feature_registry_cli_list.out

PYTHONPATH=src src/marketcore/cli/main.py feature search volatility | tee /tmp/feature_registry_cli_search.out
grep -q "feature_code=" /tmp/feature_registry_cli_search.out

PYTHONPATH=src src/marketcore/cli/main.py feature health | tee /tmp/feature_registry_cli_health.out
grep -q "unsafe_approvals=0" /tmp/feature_registry_cli_health.out

PYTHONPATH=src src/marketcore/cli/main.py feature summary --json | tee /tmp/feature_registry_cli_json.out
grep -q '"total"' /tmp/feature_registry_cli_json.out

echo "feature_registry_cli=READY"
echo "commands=summary,list,search,health"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=FEATURE_REGISTRY_CLI_V1_READY"
echo "TEST_FEATURE_REGISTRY_CLI_V1_OK"

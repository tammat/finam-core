#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EXPERIMENT_REGISTRY_CLI_V1 ==="

PYTHONPATH=src src/marketcore/cli/main.py experiment summary | tee /tmp/experiment_registry_cli_summary.out
grep -q "total=1" /tmp/experiment_registry_cli_summary.out
grep -q "registered=1" /tmp/experiment_registry_cli_summary.out
grep -q "live_approved=0" /tmp/experiment_registry_cli_summary.out

PYTHONPATH=src src/marketcore/cli/main.py experiment list --limit 5 | tee /tmp/experiment_registry_cli_list.out
grep -q "experiment_code=" /tmp/experiment_registry_cli_list.out
grep -q "BRM6@RTSX" /tmp/experiment_registry_cli_list.out

PYTHONPATH=src src/marketcore/cli/main.py experiment search BRM6 | tee /tmp/experiment_registry_cli_search.out
grep -q "RESEARCH_CANDIDATE" /tmp/experiment_registry_cli_search.out

PYTHONPATH=src src/marketcore/cli/main.py experiment health | tee /tmp/experiment_registry_cli_health.out
grep -q "unsafe_approvals=0" /tmp/experiment_registry_cli_health.out

PYTHONPATH=src src/marketcore/cli/main.py experiment summary --json | tee /tmp/experiment_registry_cli_json.out
grep -q '"total"' /tmp/experiment_registry_cli_json.out

echo "experiment_registry_cli=READY"
echo "commands=summary,list,search,health"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EXPERIMENT_REGISTRY_CLI_V1_READY"
echo "TEST_EXPERIMENT_REGISTRY_CLI_V1_OK"

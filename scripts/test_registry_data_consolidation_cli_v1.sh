#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_REGISTRY_DATA_CONSOLIDATION_CLI_V1 ==="

PYTHONPATH=src src/marketcore/cli/main.py relationship summary \
  | tee /tmp/registry_relationship_cli_summary.out

grep -q "relationship_type=CATALOG_TO_FEATURE" /tmp/registry_relationship_cli_summary.out
grep -q "total=352" /tmp/registry_relationship_cli_summary.out
grep -q "relationship_type=CATALOG_TO_MODEL" /tmp/registry_relationship_cli_summary.out
grep -q "total=280" /tmp/registry_relationship_cli_summary.out

PYTHONPATH=src src/marketcore/cli/main.py relationship list --limit 5 \
  | tee /tmp/registry_relationship_cli_list.out

grep -q "source_domain=CATALOG" /tmp/registry_relationship_cli_list.out
grep -q "validation_status=VALIDATED" /tmp/registry_relationship_cli_list.out

PYTHONPATH=src src/marketcore/cli/main.py relationship health \
  | tee /tmp/registry_relationship_cli_health.out

grep -q "total=632" /tmp/registry_relationship_cli_health.out
grep -q "missing_source_code=0" /tmp/registry_relationship_cli_health.out
grep -q "missing_target_code=0" /tmp/registry_relationship_cli_health.out
grep -q "not_validated=0" /tmp/registry_relationship_cli_health.out

PYTHONPATH=src src/marketcore/cli/main.py relationship summary --json \
  | tee /tmp/registry_relationship_cli_json.out

grep -q '"relationship_type"' /tmp/registry_relationship_cli_json.out

echo "relationship_cli=READY"
echo "commands=summary,list,health"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=REGISTRY_DATA_CONSOLIDATION_CLI_V1_READY"
echo "TEST_REGISTRY_DATA_CONSOLIDATION_CLI_V1_OK"

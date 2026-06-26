#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_KNOWLEDGE_COVERAGE_CLI_V1 ==="

PYTHONPATH=src src/marketcore/cli/main.py catalog coverage \
  | tee /tmp/knowledge_coverage_cli_v1.out

grep -q "domain=WORKFLOW" /tmp/knowledge_coverage_cli_v1.out
grep -q "object_id_coverage_pct=100.00" /tmp/knowledge_coverage_cli_v1.out
grep -q "source_system_coverage_pct=100.00" /tmp/knowledge_coverage_cli_v1.out
grep -q "discovery_coverage_pct=100.00" /tmp/knowledge_coverage_cli_v1.out
grep -q "layer_coverage_pct=100.00" /tmp/knowledge_coverage_cli_v1.out
grep -q "health_coverage_pct=100.00" /tmp/knowledge_coverage_cli_v1.out
grep -q "runtime_changed=0" /tmp/knowledge_coverage_cli_v1.out
grep -q "execution_changed=0" /tmp/knowledge_coverage_cli_v1.out
grep -q "orders_changed=0" /tmp/knowledge_coverage_cli_v1.out
grep -q "fills_changed=0" /tmp/knowledge_coverage_cli_v1.out
grep -q "micro_live_allowed=0" /tmp/knowledge_coverage_cli_v1.out

PYTHONPATH=src src/marketcore/cli/main.py catalog coverage --json \
  | tee /tmp/knowledge_coverage_cli_v1_json.out

grep -q '"domain": "WORKFLOW"' /tmp/knowledge_coverage_cli_v1_json.out
grep -q '"object_id_coverage_pct"' /tmp/knowledge_coverage_cli_v1_json.out

echo "knowledge_coverage_cli=1"
echo "json_output=1"
echo "text_output=1"
echo "VERDICT=KNOWLEDGE_COVERAGE_CLI_V1_READY"
echo "TEST_KNOWLEDGE_COVERAGE_CLI_V1_OK"

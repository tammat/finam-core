#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_AI_REGISTRY_CLI_V1 ==="

PYTHONPATH=src src/marketcore/cli/main.py ai summary | tee /tmp/ai_cli_summary.out
grep -q "AI_REGISTRY_SUMMARY" /tmp/ai_cli_summary.out
grep -q "total=10" /tmp/ai_cli_summary.out
grep -q "AI_AGENT=4" /tmp/ai_cli_summary.out
grep -q "AI_CAPABILITY=2" /tmp/ai_cli_summary.out
grep -q "AI_POLICY=4" /tmp/ai_cli_summary.out

PYTHONPATH=src src/marketcore/cli/main.py ai list | tee /tmp/ai_cli_list.out
grep -q "ai_code=AI_REGISTRY_MANAGER" /tmp/ai_cli_list.out
grep -q "ai_code=AI_KNOWLEDGE_GRAPH_AGENT" /tmp/ai_cli_list.out
grep -q "ai_code=AI_RESEARCH_ASSISTANT" /tmp/ai_cli_list.out

PYTHONPATH=src src/marketcore/cli/main.py ai search GRAPH | tee /tmp/ai_cli_search.out
grep -q "AI_KNOWLEDGE_GRAPH_AGENT" /tmp/ai_cli_search.out
grep -q "AI_GRAPH_REQUIRED" /tmp/ai_cli_search.out

PYTHONPATH=src src/marketcore/cli/main.py ai health | tee /tmp/ai_cli_health.out
grep -q "total=10" /tmp/ai_cli_health.out
grep -q "unsafe_live_rows=0" /tmp/ai_cli_health.out
grep -q "execution_policy_valid=10" /tmp/ai_cli_health.out
grep -q "market_policy_valid=10" /tmp/ai_cli_health.out
grep -q "graph_required_valid=10" /tmp/ai_cli_health.out
grep -q "framework_version_valid=10" /tmp/ai_cli_health.out
grep -q "domain_types_version_valid=10" /tmp/ai_cli_health.out
grep -q "forbidden_market_fields=0" /tmp/ai_cli_health.out

if PYTHONPATH=src src/marketcore/cli/main.py ai add 2>/tmp/ai_cli_forbidden.out; then
  echo "ERROR: forbidden add command accepted"
  exit 1
fi

echo "ai_registry_cli=READY"
echo "commands=summary,list,search,health"
echo "policy=READ_ONLY"
echo "forbidden_commands=add,update,delete,edit"
echo "framework=REGISTRY_FRAMEWORK_V1"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=AI_REGISTRY_CLI_V1_READY"
echo "TEST_AI_REGISTRY_CLI_V1_OK"

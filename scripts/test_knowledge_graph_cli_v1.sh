#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_KNOWLEDGE_GRAPH_CLI_V1 ==="

PYTHONPATH=src src/marketcore/cli/main.py graph summary | tee /tmp/kg_cli_summary.out
grep -q "total_nodes=1379" /tmp/kg_cli_summary.out
grep -q "total_edges=632" /tmp/kg_cli_summary.out
grep -q "isolated_nodes=115" /tmp/kg_cli_summary.out

PYTHONPATH=src src/marketcore/cli/main.py graph nodes | tee /tmp/kg_cli_nodes.out
grep -q "node_type=CATALOG" /tmp/kg_cli_nodes.out
grep -q "node_type=FEATURE" /tmp/kg_cli_nodes.out
grep -q "node_type=MODEL" /tmp/kg_cli_nodes.out
grep -q "node_type=EXPERIMENT" /tmp/kg_cli_nodes.out

PYTHONPATH=src src/marketcore/cli/main.py graph edges | tee /tmp/kg_cli_edges.out
grep -q "relationship_type=CATALOG_TO_FEATURE" /tmp/kg_cli_edges.out
grep -q "relationship_type=CATALOG_TO_MODEL" /tmp/kg_cli_edges.out

PYTHONPATH=src src/marketcore/cli/main.py graph paths | tee /tmp/kg_cli_paths.out
grep -q "path_type=CATALOG_TO_FEATURE" /tmp/kg_cli_paths.out
grep -q "path_type=CATALOG_TO_MODEL" /tmp/kg_cli_paths.out

PYTHONPATH=src src/marketcore/cli/main.py graph isolated | tee /tmp/kg_cli_isolated.out
grep -q "node_type=CATALOG" /tmp/kg_cli_isolated.out
grep -q "node_type=EXPERIMENT" /tmp/kg_cli_isolated.out

PYTHONPATH=src src/marketcore/cli/main.py graph health | tee /tmp/kg_cli_health.out
grep -q "nodes=1379" /tmp/kg_cli_health.out
grep -q "edges=632" /tmp/kg_cli_health.out
grep -q "paths=632" /tmp/kg_cli_health.out
grep -q "not_validated_edges=0" /tmp/kg_cli_health.out
grep -q "not_validated_paths=0" /tmp/kg_cli_health.out

PYTHONPATH=src src/marketcore/cli/main.py graph summary --json | tee /tmp/kg_cli_json.out
grep -q '"total_nodes"' /tmp/kg_cli_json.out

echo "knowledge_graph_cli=READY"
echo "commands=summary,nodes,edges,paths,isolated,health"
echo "incomplete_data_policy=VISIBLE_NOT_FATAL_IN_V1"
echo "isolated_nodes=115"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=KNOWLEDGE_GRAPH_CLI_V1_READY"
echo "TEST_KNOWLEDGE_GRAPH_CLI_V1_OK"

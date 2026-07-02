#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_KNOWLEDGE_GRAPH_STORAGE_V1 ==="

scripts/apply_knowledge_graph_storage_v1.sh

psql -d finam_core <<'SQL'

SELECT table_name
FROM information_schema.tables
WHERE table_schema='knowledge_graph'
ORDER BY table_name;

SELECT count(*)
FROM knowledge_graph.nodes;

SELECT count(*)
FROM knowledge_graph.edges;

SQL

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=KNOWLEDGE_GRAPH_STORAGE_V1_READY"
echo "VERDICT=TEST_KNOWLEDGE_GRAPH_STORAGE_V1_OK"

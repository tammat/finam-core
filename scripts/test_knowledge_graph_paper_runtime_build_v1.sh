#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_KNOWLEDGE_GRAPH_PAPER_RUNTIME_BUILD_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_knowledge_graph_paper_runtime_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_knowledge_graph_paper_runtime_v1.py \
  | tee /tmp/knowledge_graph_paper_runtime_build_v1.txt

grep -q "VERDICT=KNOWLEDGE_GRAPH_PAPER_RUNTIME_BUILD_V1_READY" \
  /tmp/knowledge_graph_paper_runtime_build_v1.txt

nodes=$(psql -At -d finam_core -c "SELECT count(*) FROM knowledge_graph.nodes WHERE domain='PAPER_RUNTIME';")
edges=$(psql -At -d finam_core -c "SELECT count(*) FROM knowledge_graph.edges WHERE domain='PAPER_RUNTIME';")

test "$nodes" -gt 0
test "$edges" -gt 0

psql -d finam_core -c "
SELECT entity_type, count(*)
FROM knowledge_graph.nodes
WHERE domain='PAPER_RUNTIME'
GROUP BY entity_type
ORDER BY entity_type;
"

psql -d finam_core -c "
SELECT edge_type, count(*)
FROM knowledge_graph.edges
WHERE domain='PAPER_RUNTIME'
GROUP BY edge_type
ORDER BY edge_type;
"

echo "nodes=$nodes"
echo "edges=$edges"
echo "VERDICT=TEST_KNOWLEDGE_GRAPH_PAPER_RUNTIME_BUILD_V1_OK"

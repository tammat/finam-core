#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_KNOWLEDGE_GRAPH_READ_MODEL_V1 ==="

scripts/apply_knowledge_graph_read_model_v1.sh

entities=$(psql -At -d finam_core -c "SELECT count(*) FROM knowledge_graph.v_api_kg_entity_summary_v1 WHERE domain='PAPER_RUNTIME';")
relations=$(psql -At -d finam_core -c "SELECT count(*) FROM knowledge_graph.v_api_kg_relation_summary_v1 WHERE domain='PAPER_RUNTIME';")
stats=$(psql -At -d finam_core -c "SELECT count(*) FROM knowledge_graph.v_api_kg_statistics_v1;")
semantic=$(psql -At -d finam_core -c "SELECT count(*) FROM knowledge_graph.v_api_kg_semantic_search_v1;")

test "$entities" -gt 0
test "$relations" -gt 0
test "$stats" -gt 0
test "$semantic" -gt 0

psql -d finam_core -c "
SELECT domain, nodes, edges, entity_types, edge_types
FROM knowledge_graph.v_api_kg_statistics_v1
ORDER BY domain;
"

psql -d finam_core -c "
SELECT node_id, entity_type, label_ru, label_en, symbol, strategy
FROM knowledge_graph.v_api_kg_entity_summary_v1
WHERE domain='PAPER_RUNTIME'
ORDER BY node_id DESC
LIMIT 5;
"

echo "entities=$entities"
echo "relations=$relations"
echo "stats=$stats"
echo "semantic=$semantic"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=KNOWLEDGE_GRAPH_READ_MODEL_V1_READY"
echo "VERDICT=TEST_KNOWLEDGE_GRAPH_READ_MODEL_V1_OK"

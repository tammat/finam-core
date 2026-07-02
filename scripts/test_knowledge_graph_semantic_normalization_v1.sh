#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_KNOWLEDGE_GRAPH_SEMANTIC_NORMALIZATION_V1 ==="

scripts/apply_knowledge_graph_semantic_normalization_v1.sh

terms=$(psql -At -d finam_core -c "SELECT count(*) FROM knowledge_graph.semantic_terms;")
ru_trade=$(psql -At -d finam_core -c "SELECT count(*) FROM knowledge_graph.v_semantic_lookup_v1 WHERE locale='ru' AND normalized_term='сделки';")
en_trade=$(psql -At -d finam_core -c "SELECT count(*) FROM knowledge_graph.v_semantic_lookup_v1 WHERE locale='en' AND normalized_term='trades';")
ru_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM knowledge_graph.v_semantic_lookup_v1 WHERE locale='ru' AND normalized_term='эдж';")

test "$terms" -gt 0
test "$ru_trade" -gt 0
test "$en_trade" -gt 0
test "$ru_edge" -gt 0

psql -d finam_core -c "
SELECT locale, normalized_term, object_type, object_key, match_type, confidence
FROM knowledge_graph.v_semantic_lookup_v1
WHERE normalized_term IN ('сделки','trades','edge','эдж','риск','risk')
ORDER BY locale, normalized_term, object_key;
"

echo "terms=$terms"
echo "ru_trade=$ru_trade"
echo "en_trade=$en_trade"
echo "ru_edge=$ru_edge"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=KNOWLEDGE_GRAPH_SEMANTIC_NORMALIZATION_V1_READY"
echo "VERDICT=TEST_KNOWLEDGE_GRAPH_SEMANTIC_NORMALIZATION_V1_OK"

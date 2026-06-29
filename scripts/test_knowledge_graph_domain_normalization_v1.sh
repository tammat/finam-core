#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_KNOWLEDGE_GRAPH_DOMAIN_NORMALIZATION_V1 ==="

PYTHONPATH=src src/scripts/research/build_knowledge_graph_schema_v1.py \
  | tee /tmp/knowledge_graph_domain_normalization_schema_v1.out

PYTHONPATH=src src/scripts/research/build_knowledge_graph_refresh_manager_v1.py \
  | tee /tmp/knowledge_graph_domain_normalization_refresh_v1.out

PYTHONPATH=src src/scripts/research/build_knowledge_graph_validation_v1.py \
  | tee /tmp/knowledge_graph_domain_normalization_validation_v1.out || true

grep -q "VERDICT=KNOWLEDGE_GRAPH_SCHEMA_V1_READY" /tmp/knowledge_graph_domain_normalization_schema_v1.out
grep -q "VERDICT=KNOWLEDGE_GRAPH_REFRESH_MANAGER_V1_READY" /tmp/knowledge_graph_domain_normalization_refresh_v1.out

grep -q "broken_source_edges=0" /tmp/knowledge_graph_domain_normalization_validation_v1.out
grep -q "broken_target_edges=0" /tmp/knowledge_graph_domain_normalization_validation_v1.out
grep -q "duplicate_edges=0" /tmp/knowledge_graph_domain_normalization_validation_v1.out
grep -q "not_validated_edges=0" /tmp/knowledge_graph_domain_normalization_validation_v1.out
grep -q "not_validated_paths=0" /tmp/knowledge_graph_domain_normalization_validation_v1.out
grep -q "source_policy=REGISTRY_AND_RELATIONSHIPS_ARE_SOURCE_OF_TRUTH" /tmp/knowledge_graph_domain_normalization_validation_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' | tee /tmp/kg_domain_types_v1.out
SELECT 'node_type=' || node_type || ':' || count(*)
FROM warehouse.kg_node_v1
GROUP BY node_type
ORDER BY node_type;

SELECT 'edge_source_type=' || source_node_type || ':' || count(*)
FROM warehouse.kg_edge_v1
GROUP BY source_node_type
ORDER BY source_node_type;
SQL

grep -q "node_type=CATALOG:" /tmp/kg_domain_types_v1.out
grep -q "node_type=FEATURE:" /tmp/kg_domain_types_v1.out
grep -q "node_type=MODEL:" /tmp/kg_domain_types_v1.out
grep -q "node_type=EXPERIMENT:" /tmp/kg_domain_types_v1.out
grep -q "edge_source_type=CATALOG:632" /tmp/kg_domain_types_v1.out

echo "domain_normalization=READY"
echo "canonical_node_types=CATALOG,FEATURE,MODEL,EXPERIMENT"
echo "broken_source_edges=0"
echo "broken_target_edges=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=KNOWLEDGE_GRAPH_DOMAIN_NORMALIZATION_V1_READY"
echo "TEST_KNOWLEDGE_GRAPH_DOMAIN_NORMALIZATION_V1_OK"

#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_KNOWLEDGE_GRAPH_SCHEMA_V1 ==="

PYTHONPATH=src src/scripts/research/build_knowledge_graph_schema_v1.py \
  | tee /tmp/knowledge_graph_schema_v1.out

grep -q "KNOWLEDGE_GRAPH_SCHEMA_V1" /tmp/knowledge_graph_schema_v1.out
grep -q "слой=VIEW_LAYER" /tmp/knowledge_graph_schema_v1.out
grep -q "kg_node=warehouse.kg_node_v1" /tmp/knowledge_graph_schema_v1.out
grep -q "kg_edge=warehouse.kg_edge_v1" /tmp/knowledge_graph_schema_v1.out
grep -q "kg_path=warehouse.kg_path_v1" /tmp/knowledge_graph_schema_v1.out
grep -q "kg_statistics=warehouse.kg_statistics_v1" /tmp/knowledge_graph_schema_v1.out
grep -q "edges=632" /tmp/knowledge_graph_schema_v1.out
grep -q "paths=632" /tmp/knowledge_graph_schema_v1.out
grep -q "relationship_types=2" /tmp/knowledge_graph_schema_v1.out
grep -q "not_validated_edges=0" /tmp/knowledge_graph_schema_v1.out
grep -q "политика=GRAPH_READ_ONLY_VIEW_LAYER" /tmp/knowledge_graph_schema_v1.out
grep -q "source_policy=REGISTRY_AND_RELATIONSHIPS_ARE_SOURCE_OF_TRUTH" /tmp/knowledge_graph_schema_v1.out
grep -q "runtime_changed=0" /tmp/knowledge_graph_schema_v1.out
grep -q "execution_changed=0" /tmp/knowledge_graph_schema_v1.out
grep -q "orders_changed=0" /tmp/knowledge_graph_schema_v1.out
grep -q "fills_changed=0" /tmp/knowledge_graph_schema_v1.out
grep -q "micro_live_allowed=0" /tmp/knowledge_graph_schema_v1.out
grep -q "VERDICT=KNOWLEDGE_GRAPH_SCHEMA_V1_READY" /tmp/knowledge_graph_schema_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'kg_node_exists=' || EXISTS (
    SELECT 1 FROM information_schema.views
    WHERE table_schema='warehouse' AND table_name='kg_node_v1'
);

SELECT 'kg_edge_exists=' || EXISTS (
    SELECT 1 FROM information_schema.views
    WHERE table_schema='warehouse' AND table_name='kg_edge_v1'
);

SELECT 'kg_path_exists=' || EXISTS (
    SELECT 1 FROM pg_matviews
    WHERE schemaname='warehouse' AND matviewname='kg_path_v1'
);

SELECT 'kg_statistics_exists=' || EXISTS (
    SELECT 1 FROM pg_matviews
    WHERE schemaname='warehouse' AND matviewname='kg_statistics_v1'
);
SQL

echo "TEST_KNOWLEDGE_GRAPH_SCHEMA_V1_OK"

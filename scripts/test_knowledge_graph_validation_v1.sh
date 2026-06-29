#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_KNOWLEDGE_GRAPH_VALIDATION_V1 ==="

PYTHONPATH=src src/scripts/research/build_knowledge_graph_validation_v1.py \
  | tee /tmp/knowledge_graph_validation_v1.out

grep -q "KNOWLEDGE_GRAPH_VALIDATION_V1" /tmp/knowledge_graph_validation_v1.out
grep -q "kg_node_rows=1379" /tmp/knowledge_graph_validation_v1.out
grep -q "kg_edge_rows=632" /tmp/knowledge_graph_validation_v1.out
grep -q "kg_path_rows=632" /tmp/knowledge_graph_validation_v1.out
grep -q "duplicate_edges=0" /tmp/knowledge_graph_validation_v1.out
grep -q "broken_source_edges=0" /tmp/knowledge_graph_validation_v1.out
grep -q "broken_target_edges=0" /tmp/knowledge_graph_validation_v1.out
grep -q "not_validated_edges=0" /tmp/knowledge_graph_validation_v1.out
grep -q "not_validated_paths=0" /tmp/knowledge_graph_validation_v1.out
grep -q "isolated_nodes=115" /tmp/knowledge_graph_validation_v1.out
grep -q "isolated_policy=CLASSIFIED_NOT_FATAL_IN_V1" /tmp/knowledge_graph_validation_v1.out
grep -q "path_policy=DEPTH_1_ONLY_IN_V1" /tmp/knowledge_graph_validation_v1.out
grep -q "source_policy=REGISTRY_AND_RELATIONSHIPS_ARE_SOURCE_OF_TRUTH" /tmp/knowledge_graph_validation_v1.out
grep -q "runtime_changed=0" /tmp/knowledge_graph_validation_v1.out
grep -q "execution_changed=0" /tmp/knowledge_graph_validation_v1.out
grep -q "orders_changed=0" /tmp/knowledge_graph_validation_v1.out
grep -q "fills_changed=0" /tmp/knowledge_graph_validation_v1.out
grep -q "micro_live_allowed=0" /tmp/knowledge_graph_validation_v1.out
grep -q "VERDICT=KNOWLEDGE_GRAPH_VALIDATION_V1_READY" /tmp/knowledge_graph_validation_v1.out

echo "TEST_KNOWLEDGE_GRAPH_VALIDATION_V1_OK"

#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_KNOWLEDGE_GRAPH_REFRESH_MANAGER_V1 ==="

PYTHONPATH=src src/scripts/research/build_knowledge_graph_refresh_manager_v1.py \
  | tee /tmp/knowledge_graph_refresh_manager_v1.out

grep -q "KNOWLEDGE_GRAPH_REFRESH_MANAGER_V1" /tmp/knowledge_graph_refresh_manager_v1.out
grep -q "refresh_lock=ACQUIRED" /tmp/knowledge_graph_refresh_manager_v1.out
grep -q "refresh_done=1" /tmp/knowledge_graph_refresh_manager_v1.out
grep -q "kg_node_rows=1379" /tmp/knowledge_graph_refresh_manager_v1.out
grep -q "kg_edge_rows=632" /tmp/knowledge_graph_refresh_manager_v1.out
grep -q "kg_path_rows=632" /tmp/knowledge_graph_refresh_manager_v1.out
grep -q "not_validated_edges=0" /tmp/knowledge_graph_refresh_manager_v1.out
grep -q "refresh_policy=ADVISORY_LOCK_PLUS_MATERIALIZED_VIEW_REFRESH" /tmp/knowledge_graph_refresh_manager_v1.out
grep -q "source_policy=REGISTRY_AND_RELATIONSHIPS_ARE_SOURCE_OF_TRUTH" /tmp/knowledge_graph_refresh_manager_v1.out
grep -q "runtime_changed=0" /tmp/knowledge_graph_refresh_manager_v1.out
grep -q "execution_changed=0" /tmp/knowledge_graph_refresh_manager_v1.out
grep -q "orders_changed=0" /tmp/knowledge_graph_refresh_manager_v1.out
grep -q "fills_changed=0" /tmp/knowledge_graph_refresh_manager_v1.out
grep -q "micro_live_allowed=0" /tmp/knowledge_graph_refresh_manager_v1.out
grep -q "VERDICT=KNOWLEDGE_GRAPH_REFRESH_MANAGER_V1_READY" /tmp/knowledge_graph_refresh_manager_v1.out

echo "TEST_KNOWLEDGE_GRAPH_REFRESH_MANAGER_V1_OK"

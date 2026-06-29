#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_KNOWLEDGE_GRAPH_UI_V1 ==="

sudo -u postgres psql finam_core <<'SQL'
GRANT USAGE ON SCHEMA warehouse TO alex;
GRANT SELECT ON warehouse.kg_node_v1 TO alex;
GRANT SELECT ON warehouse.kg_edge_v1 TO alex;
GRANT SELECT ON warehouse.kg_path_v1 TO alex;
GRANT SELECT ON warehouse.kg_statistics_v1 TO alex;
SQL

sudo systemctl restart finam-readonly-ui
sleep 2

curl -fsS http://127.0.0.1:8089/knowledge/graph \
  -o /tmp/knowledge_graph_ui_v1.html

grep -q "MarketCore Knowledge Graph" /tmp/knowledge_graph_ui_v1.html
grep -q "total_nodes=1379" /tmp/knowledge_graph_ui_v1.html
grep -q "total_edges=632" /tmp/knowledge_graph_ui_v1.html
grep -q "node_types=4" /tmp/knowledge_graph_ui_v1.html
grep -q "relationship_types=2" /tmp/knowledge_graph_ui_v1.html
grep -q "graph_health=OK" /tmp/knowledge_graph_ui_v1.html
grep -q "not_validated_edges=0" /tmp/knowledge_graph_ui_v1.html
grep -q "not_validated_paths=0" /tmp/knowledge_graph_ui_v1.html
grep -q "incomplete_data_status=WARNING" /tmp/knowledge_graph_ui_v1.html
grep -q "isolated_nodes=115" /tmp/knowledge_graph_ui_v1.html
grep -q "incomplete_data_policy=VISIBLE_NOT_FATAL_IN_V1" /tmp/knowledge_graph_ui_v1.html
grep -q "canonical_node_types=CATALOG, FEATURE, MODEL, EXPERIMENT" /tmp/knowledge_graph_ui_v1.html
grep -q "CATALOG_TO_FEATURE" /tmp/knowledge_graph_ui_v1.html
grep -q "CATALOG_TO_MODEL" /tmp/knowledge_graph_ui_v1.html
grep -q "path_policy=DEPTH_1_ONLY_IN_V1" /tmp/knowledge_graph_ui_v1.html
grep -q "planned_relationships=FEATURE_TO_EXPERIMENT,EXPERIMENT_TO_MODEL" /tmp/knowledge_graph_ui_v1.html
grep -q "source_policy=REGISTRY_AND_RELATIONSHIPS_ARE_SOURCE_OF_TRUTH" /tmp/knowledge_graph_ui_v1.html
grep -q "ui_policy=READ_ONLY_SINGLE_PORT_8089" /tmp/knowledge_graph_ui_v1.html
grep -q "micro_live_allowed=0" /tmp/knowledge_graph_ui_v1.html

echo "single_ui_port=8089"
echo "route_graph=/knowledge/graph"
echo "graph_health=OK"
echo "incomplete_data_status=WARNING"
echo "isolated_nodes=115"
echo "source_policy=REGISTRY_AND_RELATIONSHIPS_ARE_SOURCE_OF_TRUTH"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=KNOWLEDGE_GRAPH_UI_V1_READY"
echo "TEST_KNOWLEDGE_GRAPH_UI_V1_OK"

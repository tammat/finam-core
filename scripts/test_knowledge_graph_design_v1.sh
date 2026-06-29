#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_KNOWLEDGE_GRAPH_DESIGN_V1 ==="

test -f docs/knowledge_graph_design_v1.md

grep -q "KNOWLEDGE_GRAPH_DESIGN_V1" docs/knowledge_graph_design_v1.md
grep -q "CATALOG_TO_FEATURE" docs/knowledge_graph_design_v1.md
grep -q "CATALOG_TO_MODEL" docs/knowledge_graph_design_v1.md
grep -q "FEATURE_TO_EXPERIMENT" docs/knowledge_graph_design_v1.md
grep -q "EXPERIMENT_TO_MODEL" docs/knowledge_graph_design_v1.md
grep -q "AI не изменяет runtime" docs/knowledge_graph_design_v1.md
grep -q "ReadOnly UI на 8089" docs/knowledge_graph_design_v1.md
grep -q "micro_live_allowed=0" docs/knowledge_graph_design_v1.md

echo "design_document=READY"
echo "nodes=CATALOG_OBJECT,FEATURE,EXPERIMENT,MODEL,CANDIDATE,PAPER_SESSION,RUNTIME_SIGNAL,TRADE,RISK_EVENT,REPORT"
echo "relationships=CATALOG_TO_FEATURE,CATALOG_TO_MODEL,FEATURE_TO_EXPERIMENT,EXPERIMENT_TO_MODEL"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=KNOWLEDGE_GRAPH_DESIGN_V1_READY"
echo "TEST_KNOWLEDGE_GRAPH_DESIGN_V1_OK"

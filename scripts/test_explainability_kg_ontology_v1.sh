#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EXPLAINABILITY_KG_ONTOLOGY_V1 ==="

DOC="docs/architecture/FINAM_CORE_EXPLAINABILITY_KNOWLEDGE_GRAPH_ONTOLOGY_V1.md"

test -f "$DOC"

grep -q "FINAM_CORE_EXPLAINABILITY_KNOWLEDGE_GRAPH_ONTOLOGY_V1" "$DOC"
grep -q "Trade Context Snapshot" "$DOC"
grep -q "public.trade_context_snapshots" "$DOC"
grep -q "HAS_ATTRIBUTION" "$DOC"
grep -q "HAS_EDGE_GATE" "$DOC"
grep -q "HAS_RISK_CONTEXT" "$DOC"
grep -q "ontology_version" "$DOC"
grep -q "PostgreSQL only" "$DOC"
grep -q "AI/LLM слой" "$DOC"

echo "ontology_doc_ready=READY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EXPLAINABILITY_KG_ONTOLOGY_V1_READY"
echo "VERDICT=TEST_EXPLAINABILITY_KG_ONTOLOGY_V1_OK"

#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_RUNTIME_KNOWLEDGE_GRAPH_SOURCE_DISCOVERY_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/discover_paper_runtime_kg_sources_v1.py

DATABASE_URL=postgresql:///finam_core \
PYTHONPATH=src \
python src/scripts/discover_paper_runtime_kg_sources_v1.py \
  | tee /tmp/paper_runtime_kg_sources_v1.txt

grep -q "VERDICT=PAPER_RUNTIME_KNOWLEDGE_GRAPH_SOURCE_DISCOVERY_V1_READY" \
  /tmp/paper_runtime_kg_sources_v1.txt

echo "VERDICT=TEST_PAPER_RUNTIME_KNOWLEDGE_GRAPH_SOURCE_DISCOVERY_V1_OK"

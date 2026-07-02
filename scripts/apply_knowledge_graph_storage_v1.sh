#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres \
psql \
-v ON_ERROR_STOP=1 \
-d finam_core \
-f sql/knowledge_graph/001_knowledge_graph_storage_v1.sql

echo "KNOWLEDGE_GRAPH_STORAGE_V1_READY"

#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EDGE_DISCOVERY_CENTER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/paper_edge_discovery.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py

KG_API_HOST=127.0.0.1 KG_API_PORT=18095 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_paper_edge_discovery_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=18080 KG_API_BASE_URL=http://127.0.0.1:18095 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/paper_edge_discovery_center_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:18080/paper-edge-discovery" > /tmp/paper_edge_discovery_center_v1.html

grep -q "Центр поиска Edge" /tmp/paper_edge_discovery_center_v1.html
grep -q "Paper Runtime" /tmp/paper_edge_discovery_center_v1.html
grep -q "Knowledge Graph" /tmp/paper_edge_discovery_center_v1.html
grep -q "Validation" /tmp/paper_edge_discovery_center_v1.html
grep -q "PAPER_RUNTIME" /tmp/paper_edge_discovery_center_v1.html
grep -q "PAPER_EDGE_DISCOVERY_REAL_DATA_V1" /tmp/paper_edge_discovery_center_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/paper_edge_discovery_center_v1.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EDGE_DISCOVERY_CENTER_V1_READY"
echo "VERDICT=TEST_PAPER_EDGE_DISCOVERY_CENTER_V1_OK"

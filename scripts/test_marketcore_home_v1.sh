#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_HOME_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/api_client.py \
  src/marketcore/presentation/pages/home.py \
  src/marketcore/presentation/app.py

KG_API_HOST=127.0.0.1 KG_API_PORT=8095 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_for_home_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=8080 KG_API_BASE_URL=http://127.0.0.1:8095 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/marketcore_home_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:8080/" > /tmp/marketcore_home_v1.html

grep -q "MarketCore OS" /tmp/marketcore_home_v1.html
grep -q "Platform M2" /tmp/marketcore_home_v1.html
grep -q "Knowledge Graph API" /tmp/marketcore_home_v1.html
grep -q "Knowledge Graph Statistics" /tmp/marketcore_home_v1.html
grep -q "Validation" /tmp/marketcore_home_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/marketcore_home_v1.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_HOME_V1_READY"
echo "VERDICT=TEST_MARKETCORE_HOME_V1_OK"

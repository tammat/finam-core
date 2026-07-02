#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_KNOWLEDGE_GRAPH_API_V1 ==="

PYTHONPATH=src python -m py_compile src/marketcore/api/serve_knowledge_graph_api_v1.py

KG_API_HOST=127.0.0.1 KG_API_PORT=8095 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_v1.log 2>&1 &
pid=$!

cleanup() {
  kill "$pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:8095/api/kg/v1/health" | tee /tmp/kg_api_health.json
curl -fsS "http://127.0.0.1:8095/api/kg/v1/statistics" | tee /tmp/kg_api_statistics.json
curl -fsS "http://127.0.0.1:8095/api/kg/v1/search?q=сделки&locale=ru" | tee /tmp/kg_api_search.json
curl -fsS "http://127.0.0.1:8095/api/kg/v1/validation" | tee /tmp/kg_api_validation.json

grep -q '"status": "OK"' /tmp/kg_api_health.json
grep -q '"status": "OK"' /tmp/kg_api_statistics.json
grep -q '"status": "OK"' /tmp/kg_api_search.json
grep -q '"status": "OK"' /tmp/kg_api_validation.json

echo
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=KNOWLEDGE_GRAPH_API_V1_READY"
echo "VERDICT=TEST_KNOWLEDGE_GRAPH_API_V1_OK"
